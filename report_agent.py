"""
レポート作成代行エージェント
"""
import os
import time
import asyncio
from dotenv import load_dotenv
import streamlit as st
from strands import Agent
from strands.models.ollama import OllamaModel
from strands.tools import tool
from strands.tools.mcp.mcp_client import  MCPClient
from strands.agent.conversation_manager import SlidingWindowConversationManager
from mcp.client.streamable_http import streamable_http_client
from Markdown2docx import Markdown2docx


load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY is not set in environment variables.")


# ファイル保存用のディレクトリを作成
if not os.path.exists("reports"):
    os.makedirs("reports")


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
"""

# MCPクライアントのインスタンスを作成
mcp_client = MCPClient(
    lambda: streamable_http_client(
        f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
    )
)

# Ollamaモデルのインスタンスを作成
ollama_model = OllamaModel(
    host="http://localhost:11434",
    model_id="qwen3.5:2b"
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


st.title("レポート作成代行エージェント")

# セッション状態の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_manager" not in st.session_state:
    st.session_state.conversation_manager = SlidingWindowConversationManager(window_size=5)

if "agent_messages" not in st.session_state:
    st.session_state.agent_messages = []

# 会話履歴を表示
for message in st.session_state.messages:
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
            previous_agent_messages = st.session_state.agent_messages.copy()

            # ストリーミング応答を実行
            full_response, updated_agent_messages = asyncio.run(stream_response(
                prompt,
                response_placeholder,
                previous_agent_messages,
            ))

            # Agent内部の正しいメッセージ形式を次ターンへ引き継ぐ
            st.session_state.agent_messages = updated_agent_messages

            # ユーザーメッセージを履歴に追加
            st.session_state.messages.append({"role": "user", "content": prompt})

            # AIの応答を履歴に追加
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            error_message = f"エラーが発生しました: {str(e)}"
            st.error(error_message)
            # エラーの場合もユーザーメッセージを履歴に追加
            st.session_state.messages.append({"role": "user", "content": prompt})
            # エラーメッセージも履歴に追加
            st.session_state.messages.append({"role": "assistant", "content": error_message})
