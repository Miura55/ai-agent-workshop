"""
Step 4: 会話履歴を保存する
"""
import os
from dotenv import load_dotenv
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
あなたは、Web検索を行うAIアシスタントです。ユーザーの質問に対して、Web検索を行い、最新の情報を提供してください。
必要に応じて、MCPクライアントを使用して、Web検索ツールを呼び出すことができます。
## 要件
- ユーザーの質問に対して、Web検索を行い、最新の情報を提供してください。
- MCPクライアントを使用して、Web検索ツールを呼び出すことができます。
- 公平性を保ち、偏見のない情報を提供してください。
- ユーザーが求めている情報を正確に理解し、適切な検索クエリを生成してください。
- 回答は日本語で提供してください。
- 参考にしたURLも提供してください。
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

tool_use_ids = []  # 使用したツールのIDを記録するリスト
def callback_handler(**kwargs):
    if "data" in kwargs:
        # Log the streamed data chunks
        print(kwargs["data"], end="")
    elif "current_tool_use" in kwargs:
        tool = kwargs["current_tool_use"]
        if tool["toolUseId"] not in tool_use_ids:
            # Log the tool use
            print(f"\n[Using tool: {tool.get('name')}]")
            tool_use_ids.append(tool["toolUseId"])

# Agentを作成し、OllamaモデルとMCPクライアントを登録
with mcp_client:
    agent = Agent(
        model=ollama_model,
        tools=mcp_client.list_tools_sync(),  # MCPクライアントをエージェントに登録
        system_prompt=SYSTEM_PROMPT,
        conversation_manager=conversation_manager,  # 会話履歴を管理するConversationManagerをエージェントに登録
        callback_handler=callback_handler  # コールバック関数をエージェントに登録
    )

    while True:
        try:
            user_input = input("ユーザー: ")
            if user_input.lower() in ["exit", "quit"]:
                print("エージェントとの会話を終了します。")
                break
            response = agent(user_input)
            print(f"\nエージェント: {response.message}")
        except KeyboardInterrupt:
            print("\nエージェントとの会話を終了します。")
            break
