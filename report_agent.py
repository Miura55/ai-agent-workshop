"""
レポート作成代行エージェント
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
以下のフォーマットでレポートを生成してください。

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
    agent("フーリエ変換の概要を調べてレポートにまとめてください")
