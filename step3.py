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

# MCPクライアントのインスタンスを作成
mcp_client = MCPClient(
    lambda: streamable_http_client(
        f"https://mcp.tavily.com/mcp/?tavilyApiKey={TRAVILY_API_KEY}"
    )
)

# Ollamaモデルのインスタンスを作成
ollama_model = OllamaModel(
    host="http://localhost:11434",
    model_id="qwen3.5:0.8b"
)

# Agentを作成し、OllamaモデルとMCPクライアントを登録
with mcp_client:
    agent = Agent(
        model=ollama_model,
        tools=mcp_client.list_tools_sync()  # MCPクライアントをエージェントに登録
    )

    # エージェントを使用
    agent("Pythonのリリース情報を教えてください。")
