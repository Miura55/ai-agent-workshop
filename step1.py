"""
Step1: LLMを呼び出してみる
"""
from strands import Agent
from strands.models.ollama import OllamaModel


# Ollamaモデルのインスタンスを作成
ollama_model = OllamaModel(
    host="http://localhost:11434",
    model_id="granite4:3b"
)

# Agentを作成し、Ollamaモデルを登録
agent = Agent(
    model=ollama_model
)

# エージェントを使用
agent("AIとは何ですか？")
