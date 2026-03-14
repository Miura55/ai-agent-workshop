"""
Step1: LLMを呼び出してみる
"""
from strands import Agent
from strands.models.ollama import OllamaModel
from strands.agent.conversation_manager import SlidingWindowConversationManager


# Ollamaモデルのインスタンスを作成
ollama_model = OllamaModel(
    host="http://localhost:11434",
    model_id="qwen3.5:2b"
)

# Agentを作成し、Ollamaモデルを登録
agent = Agent(
    model=ollama_model,
    conversation_manager=SlidingWindowConversationManager(window_size=5)  # 会話履歴を管理するConversationManagerをエージェントに登録
)

while True:
    user_input = input("ユーザー: ")
    if user_input.lower() in ["exit", "quit"]:
        print("エージェントとの会話を終了します。")
        break
    response = agent(user_input)
    print(f"エージェント: {response}\n")
