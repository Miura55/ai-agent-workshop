"""
Step3: MCPクライアントとの連携
"""
import os
from dotenv import load_dotenv
from strands import Agent
from strands.models.ollama import OllamaModel
from strands.tools.mcp.mcp_client import  MCPClient
from mcp.client.streamable_http import streamable_http_client


load_dotenv()
TRAVILY_API_KEY = os.getenv("TRAVILY_API_KEY")
if not TRAVILY_API_KEY:
    raise ValueError("TRAVILY_API_KEY is not set in environment variables.")

SYSTEM_PROMPT = """
あなたは、Web検索を行うAIアシスタントです。ユーザーの質問に対して、Web検索を行い、最新の情報を提供してください。必要に応じて、MCPクライアントを使用して、Web検索ツールを呼び出すことができます。
## 要件
- ユーザーの質問に対して、Web検索を行い、最新の情報を提供してください。
- MCPクライアントを使用して、Web検索ツールを呼び出すことができます。
- 公平性を保ち、偏見のない情報を提供してください。
- ユーザーが
- 参考にしたURLも提供してください。
"""

# MCPクライアントのインスタンスを作成
mcp_client = MCPClient(
    lambda: streamable_http_client(
        f"https://mcp.tavily.com/mcp/?tavilyApiKey={TRAVILY_API_KEY}"
    )
)

# Ollamaモデルのインスタンスを作成
ollama_model = OllamaModel(
    host="http://localhost:11434",
    model_id="qwen3.5:2b"
)

# Agentを作成し、OllamaモデルとMCPクライアントを登録
with mcp_client:
    agent = Agent(
        model=ollama_model,
        tools=mcp_client.list_tools_sync(),  # MCPクライアントをエージェントに登録
        system_prompt=SYSTEM_PROMPT
    )

    # エージェントを使用
    agent("AIの最新トレンドを調べてください。")
