"""
レポート作成代行エージェント
"""
import os
import time
import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st
from strands import Agent
from strands.models.ollama import OllamaModel
from strands.tools import tool
from strands.tools.mcp.mcp_client import MCPClient
from strands.agent.conversation_manager import SlidingWindowConversationManager
from mcp.client.streamable_http import streamable_http_client
import Markdown2docx as markdown2docx_module
from Markdown2docx import HtmlListParser, Markdown2docx
from mem0 import Memory


load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY is not set in environment variables.")


# ファイル保存用のディレクトリを作成
if not os.path.exists("reports"):
    os.makedirs("reports")

SESSIONS_DIR = Path("sessions")
SESSIONS_DIR.mkdir(exist_ok=True)
MEM0_DATA_DIR = SESSIONS_DIR / "mem0_qdrant"
MEM0_HISTORY_DB = SESSIONS_DIR / "mem0_history.db"
@st.cache_resource
def get_mem0_client():
    return Memory.from_config({
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "report_agent_memories",
                "path": str(MEM0_DATA_DIR),
                "embedding_model_dims": 768,
            },
        },
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "gemma4:e2b",
                "temperature": 0,
                "ollama_base_url": "http://localhost:11434",
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text:latest",
                "ollama_base_url": "http://localhost:11434",
            },
        },
        "history_db_path": str(MEM0_HISTORY_DB),
    })


mem0_error = None
try:
    mem0_client = get_mem0_client()
except Exception as exc:
    mem0_client = None
    mem0_error = str(exc)


SYSTEM_PROMPT = """
あなたはレポート作成を代行するエージェントです。
ユーザーの質問に対して、Web検索を行い、最新の情報を提供してください。
必要に応じて、MCPクライアントを使用して、Web検索ツールを呼び出すことができます。
また、レポートの内容をファイルに保存するためのツールも用意されています。

## 要件
- MCPクライアントを使用して、Web検索ツールを呼び出すことができます。
- 公平性を保ち、偏見のない情報を提供してください。
- ユーザーが求めている情報を正確に理解し、適切な検索クエリを生成してください。
- レポートの内容をファイルに保存するときは、`write_report_to_docx` を使用してください。
- 回答は日本語で提供してください。
- レポートにまとめる際は、以下の構成に従ってください。

### 構成
- 序論にはレポートや論文の問い、目的、研究の背景などを書いてください。どのような資料や
データを用いるかを示すといいです。
- 本論には、複数の章や節で答えに至るべく議論を展開してください。必要に応じて、Web検索で得られた情報を引用してください。
- 結論には、本論の内容を要約し、序論で提起した問いの答えを簡潔に書いてください。
- 参考文献には、Web検索で得られた情報のURLを記載してください。

### Markdownの記法（Word出力向け）
- 見出しは `#`、`##`、`###` を使い、見出し自体に章番号を付けないでください。番号が資料に明記されている場合や、ユーザーが番号付けを指定した場合に限り番号を付けてください。
- 箇条書きの記号は必ずハイフンと半角スペースの `- ` を使ってください。`* ` や `+ ` を箇条書き記号として使わないでください。順序のない項目には番号を付けないでください。
- 番号付きリストは、順序が重要な手順・順位・段階、および参考文献一覧に使ってください。番号付きリストは各項目を `1. ` の形式で始め、Markdownの自動採番に任せてください。項目の途中で番号をリセットしたり、番号と箇条書きを混在させたりしないでください。
- 番号付きリストに `#` を番号記号として使わないでください。Word向けの番号付きリストは必ず `1. ` 形式で記述してください。
- 参考文献は番号付きリストにし、本文中で番号を使って参照する場合は一覧の番号と一致させてください。
- 出典に基づく記述の直後に、対応する参考文献番号を `[1]` の形式で本文中に明記してください。複数の出典を使う場合は `[1][2]` のようにすべて示し、参考文献一覧の番号と一致させてください。
- 太字の装飾（`**...**`）は使用しないでください。
- 箇条書きの階層は、親項目の次の行に半角スペース4つを入れて `- ` で始めてください。階層を表すために全角スペースやタブを使わず、同じ階層ではインデント幅を統一してください。
- 箇条書き項目は原則として1項目につき1段落にし、項目間に空行を挟まないでください。リストを終えるときは次の見出しまたは本文との間に空行を入れてください。
- 本文中で番号や箇条書きに見える記号を使う必要がある場合は、リストとして誤認されないよう文章に組み込んでください。
- 出力前に、すべての箇条書きが `- ` で始まっていることを確認し、`* ` または `+ ` で始まる箇条書きがあれば `- ` に直してください。あわせて、意図しない番号の追加、番号の重複・飛び、箇条書きの階層とインデント、リストの混在がないか確認してください。
"""


class StableHtmlListParser(HtmlListParser):
    """Keep list type local to each list and emit each item as one paragraph."""

    def __init__(self):
        super().__init__()
        self.list_styles = []
        self.list_items = []

    def _emit_item_text(self, item):
        text = " ".join("".join(item["parts"]).split())
        if not text:
            return
        styles = self.list_styles[item["level"]]
        style = styles[min(item["level"], len(styles) - 1)]
        self.doc.add_paragraph(text, style=style)
        item["parts"].clear()

    def handle_starttag(self, tag, attrs):
        if tag in ("ul", "ol"):
            if self.list_items:
                self._emit_item_text(self.list_items[-1])
            styles = ["List Bullet", "List Bullet 2", "List Bullet 3"]
            if tag == "ol":
                styles = ["List Number", "List Number 2", "List Number 3"]
            self.list_styles.append(styles)
            super().handle_starttag(tag, attrs)
        elif tag == "li":
            self.list_items.append({"level": self.list_level, "parts": []})
        elif tag == "br" and self.list_items:
            self.list_items[-1]["parts"].append(" ")

    def handle_endtag(self, tag):
        if tag == "li" and self.list_items:
            item = self.list_items.pop()
            self._emit_item_text(item)
        elif tag in ("ul", "ol"):
            super().handle_endtag(tag)
            if self.list_styles:
                self.list_styles.pop()

    def handle_data(self, data):
        if self.list_items:
            self.list_items[-1]["parts"].append(data)


# Markdown2docx mutates HtmlListParser.lists for ordered lists and does not
# restore it for later unordered lists. Use a parser that tracks each list locally.
markdown2docx_module.HtmlListParser = StableHtmlListParser

# MCPクライアントのインスタンスを作成
mcp_client = MCPClient(
    lambda: streamable_http_client(
        f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
    )
)

# Ollamaモデルのインスタンスを作成
ollama_model = OllamaModel(
    host="http://localhost:11434",
    model_id="gemma4:e2b"
)


@tool
def write_report_to_docx(report_content: str) -> str:
    """レポート内容をDOCXファイルに保存する

    Args:
        report_content (str): レポートの内容（Markdown形式）

    Returns:
        str: 保存されたファイルのパス
    """
    tmp_file = f"reports/{int(time.time())}"
    with open(f"{tmp_file}.md", "w", encoding="utf-8") as f:
        f.write(report_content)

    try:
        converter = Markdown2docx(tmp_file)
        converter.eat_soup()
        converter.save()
    except Exception as e:
        return f"レポートの保存中にエラーが発生しました: {str(e)}"

    return f"レポートが保存されました: {tmp_file}.docx"


async def stream_response(conversation_prompt: str, placeholder, agent_messages):
    """リアルタイムストリーミング表示を行う"""
    streamed_response = ""

    with mcp_client:
        # 会話履歴はConversationManagerで管理する
        agent = Agent(
            model=ollama_model,
            tools=mcp_client.list_tools_sync() + [write_report_to_docx],
            system_prompt=SYSTEM_PROMPT,
            messages=agent_messages,
            conversation_manager=st.session_state.conversation_manager,
        )

        async for event in agent.stream_async(prompt=conversation_prompt):
            # ストリーミングイベントからテキストを取得
            text = ""
            if "event" in event:
                event_data = event.get("event", {})
                if "contentBlockDelta" in event_data:
                    delta = event_data.get("contentBlockDelta", {}).get("delta", {})
                    text = delta.get("text", "")
                elif "text" in event_data:
                    text = event_data.get("text", "")
            elif "current_tool_use" in event:
                # ツール使用イベントからテキストを取得
                tool_use = event.get("current_tool_use", {})
                text = f"\n\n```\n⚒️ Using tool: {tool_use.get('name', '')}\n```\n\n"

            if text:
                streamed_response += text
                # プレースホルダーに現在の内容を表示
                placeholder.markdown(streamed_response)

    return streamed_response, agent.messages


def _session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def _load_sessions() -> dict:
    sessions = {}
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("id") == path.stem:
                uuid.UUID(hex=data["id"])
                sessions[data["id"]] = data
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return sessions


def _save_session(session: dict) -> None:
    path = _session_path(session["id"])
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _new_session() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    session = {"id": uuid.uuid4().hex, "title": "新しい会話", "updated_at": now,
               "messages": [], "agent_messages": []}
    _save_session(session)
    return session


def _remember_exchange(session_id: str, user_text: str, assistant_text: str) -> None:
    if not mem0_client:
        return
    try:
        mem0_client.add([
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ], user_id=session_id)
    except Exception as exc:
        st.sidebar.caption(f"mem0への保存に失敗しました: {exc}")


def _find_session_memories(session_id: str, query: str) -> str:
    if not mem0_client:
        return ""
    try:
        result = mem0_client.search(query, filters={"user_id": session_id})
        memories = result.get("results", []) if isinstance(result, dict) else []
        snippets = [item.get("memory", "") for item in memories if item.get("memory")]
        return "\n".join(f"- {snippet}" for snippet in snippets[:5])
    except Exception as exc:
        st.sidebar.caption(f"mem0の検索に失敗しました: {exc}")
        return ""


def _delete_session_memories(session_id: str) -> None:
    if not mem0_client:
        return
    try:
        mem0_client.delete_all(user_id=session_id)
    except Exception as exc:
        st.sidebar.caption(f"mem0の記憶削除に失敗しました: {exc}")


st.set_page_config(page_title="レポート作成代行エージェント", page_icon="📝")
st.title("レポート作成代行エージェント")

# セッション一覧を読み込み、サイドバーから会話を切り替える
sessions = _load_sessions()
if "active_session_id" not in st.session_state or st.session_state.active_session_id not in sessions:
    initial_session = _new_session()
    sessions[initial_session["id"]] = initial_session
    st.session_state.active_session_id = initial_session["id"]

with st.sidebar:
    st.subheader("会話セッション")
    if st.button("＋ 新しい会話", use_container_width=True):
        new_session = _new_session()
        st.session_state.active_session_id = new_session["id"]
        st.rerun()

    session_ids = sorted(sessions, key=lambda sid: sessions[sid].get("updated_at", ""), reverse=True)
    for sid in session_ids:
        session = sessions[sid]
        col_select, col_delete = st.columns([5, 1])
        if col_select.button(session.get("title", "新しい会話"), key=f"select_{sid}",
                             type="primary" if sid == st.session_state.active_session_id else "secondary",
                             use_container_width=True):
            st.session_state.active_session_id = sid
            st.rerun()
        if col_delete.button("×", key=f"delete_{sid}", help="この会話を削除"):
            _session_path(sid).unlink(missing_ok=True)
            _delete_session_memories(sid)
            if sid == st.session_state.active_session_id:
                remaining = [other_id for other_id in session_ids if other_id != sid]
                if remaining:
                    st.session_state.active_session_id = remaining[0]
                else:
                    replacement = _new_session()
                    st.session_state.active_session_id = replacement["id"]
            st.rerun()

    if mem0_client:
        st.caption("mem0のローカル記憶: 有効（Ollama + ローカルQdrant）")
    else:
        st.caption(f"mem0を初期化できませんでした: {mem0_error}")

active_session = sessions.get(st.session_state.active_session_id) or _new_session()
st.session_state.active_session_id = active_session["id"]
with st.sidebar.form("rename_active_session"):
    renamed_title = st.text_input("選択中の会話名", value=active_session.get("title", "新しい会話"),
                                  max_chars=60)
    if st.form_submit_button("名前を保存") and renamed_title.strip():
        active_session["title"] = renamed_title.strip()
        active_session["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_session(active_session)
        st.rerun()

if "loaded_session_id" not in st.session_state or st.session_state.loaded_session_id != active_session["id"]:
    st.session_state.loaded_session_id = active_session["id"]
    st.session_state.conversation_manager = SlidingWindowConversationManager(window_size=5)

# 会話履歴を表示
for message in active_session.get("messages", []):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if prompt := st.chat_input():
    # ユーザーメッセージを表示
    with st.chat_message("user"):
        st.markdown(prompt)

    print("prompt:", prompt)  # デバッグ用にプロンプトをコンソールに出力

    # アシスタント応答用のプレースホルダーを作成
    with st.chat_message("assistant"):
        response_placeholder = st.empty()

        try:
            previous_agent_messages = active_session.get("agent_messages", []).copy()
            memories = _find_session_memories(active_session["id"], prompt)
            prompt_with_memories = prompt
            if memories:
                prompt_with_memories = (
                    f"過去のこのセッションに関連する記憶です。必要な場合だけ参考にしてください。\n"
                    f"{memories}\n\n今回の依頼: {prompt}"
                )

            # ストリーミング応答を実行
            full_response, updated_agent_messages = asyncio.run(stream_response(
                prompt_with_memories,
                response_placeholder,
                previous_agent_messages,
            ))

            # Agent内部の正しいメッセージ形式を次ターンへ引き継ぐ
            active_session["agent_messages"] = updated_agent_messages
            active_session.setdefault("messages", []).append({"role": "user", "content": prompt})
            active_session["messages"].append({"role": "assistant", "content": full_response})
            if active_session["title"] == "新しい会話":
                active_session["title"] = prompt[:32] + ("…" if len(prompt) > 32 else "")
            active_session["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_session(active_session)
            _remember_exchange(active_session["id"], prompt, full_response)

        except Exception as e:
            error_message = f"エラーが発生しました: {str(e)}"
            st.error(error_message)
            active_session.setdefault("messages", []).append({"role": "user", "content": prompt})
            active_session["messages"].append({"role": "assistant", "content": error_message})
            active_session["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_session(active_session)
