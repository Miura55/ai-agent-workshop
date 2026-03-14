"""
レポート作成代行エージェント
"""
import os
import asyncio
from dotenv import load_dotenv
import streamlit as st
from strands import Agent
from strands.models.ollama import OllamaModel
from strands.tools.mcp.mcp_client import  MCPClient
from strands.agent.conversation_manager import SlidingWindowConversationManager
from mcp.client.streamable_http import streamable_http_client


load_dotenv()
TRAVILY_API_KEY = os.getenv("TRAVILY_API_KEY")
if not TRAVILY_API_KEY:
    raise ValueError("TRAVILY_API_KEY is not set in environment variables.")

SYSTEM_PROMPT = """
あなたはレポート作成を代行するエージェントです。
ユーザーの質問に対して、Web検索を行い、最新の情報を提供してください。
必要に応じて、MCPクライアントを使用して、Web検索ツールを呼び出すことができます。

## 要件
- MCPクライアントを使用して、Web検索ツールを呼び出すことができます。
- 公平性を保ち、偏見のない情報を提供してください。
- ユーザーが求めている情報を正確に理解し、適切な検索クエリを生成してください。
- 回答は日本語で提供してください。

## 構成
- 序論にはレポートや論文の問い、目的、研究の背景などを書いてください。どのような資料や
データを用いるかを示すといいです。
- 本論には、複数の章や節で答えに至るべく議論を展開してください。必要に応じて、Web検索で得られた情報を引用してください。
- 結論には、本論の内容を要約し、序論で提起した問いの答えを簡潔に書いてください。
- 参考文献には、Web検索で得られた情報のURLを記載してください。

## フォーマット
レポートにまとめるときは、以下のフォーマットに従ってください。

```md
## 序論
## 本論
## 結論
## 参考文献
```
"""

# MCPクライアントのインスタンスを作成
mcp_client = MCPClient(
    lambda: streamable_http_client(
        f"https://mcp.tavily.com/mcp/?tavilyApiKey={TRAVILY_API_KEY}"
    )
)

# 会話履歴を管理するためのConversationManagerを作成
conversation_manager = SlidingWindowConversationManager(window_size=5)

# Ollamaモデルのインスタンスを作成
ollama_model = OllamaModel(
    host="http://localhost:11434",
    model_id="qwen3.5:2b"
)

st.title("レポート作成代行エージェント")

# セッション状態の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []

# 会話履歴を表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


async def stream_response(prompt: str, placeholder, messages_history):
    """リアルタイムストリーミング表示を行う"""
    streamed_response = ""

    with mcp_client:
        # 過去の会話履歴をAgentに渡す
        agent = Agent(
            model=ollama_model,
            tools=mcp_client.list_tools_sync(),
            system_prompt=SYSTEM_PROMPT,
            messages=messages_history  # 会話履歴をAgentに渡す
        )

        async for event in agent.stream_async(prompt=prompt):
            # ストリーミングイベントからテキストを取得
            text = ""
            if "event" in event:
                event_data = event.get("event", {})
                if "contentBlockDelta" in event_data:
                    delta = event_data.get("contentBlockDelta", {}).get("delta", {})
                    text = delta.get("text", "")
                elif "text" in event_data:
                    text = event_data.get("text", "")

            if text:
                streamed_response += text
                # プレースホルダーに現在の内容を表示
                placeholder.markdown(streamed_response)

    return streamed_response


if prompt := st.chat_input():
    # ユーザーメッセージを表示
    with st.chat_message("user"):
        st.markdown(prompt)

    print("prompt:", prompt)  # デバッグ用にプロンプトをコンソールに出力

    # アシスタント応答用のプレースホルダーを作成
    with st.chat_message("assistant"):
        response_placeholder = st.empty()

        try:
            # 現在の会話履歴をAgentに渡す（現在のユーザーメッセージは除く）
            messages_history = st.session_state.messages.copy()

            # ストリーミング応答を実行（会話履歴を含む）
            full_response = asyncio.run(stream_response(prompt, response_placeholder, messages_history))

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
