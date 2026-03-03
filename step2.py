"""
Step2: 簡単なツール連携
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from strands import Agent
from strands.models.ollama import OllamaModel
from strands.tools import tool


@tool
def get_current_time(timezone: str = "UTC") -> str:
    """現在の日時を返すツール"""
    now = datetime.now(ZoneInfo(timezone))
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")

# Ollamaモデルのインスタンスを作成
ollama_model = OllamaModel(
    host="http://localhost:11434",
    model_id="qwen3.5:0.8b"
)

# Agentを作成し、Ollamaモデルとget_current_timeツールを登録
agent = Agent(
    model=ollama_model,
    tools=[get_current_time]  # get_current_timeツールをエージェントに登録
)

# エージェントを使用
agent("ニューヨークの現在の日時を教えてください。")
