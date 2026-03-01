from strands import Agent
from strands.models.ollama import OllamaModel
from strands.tools import tool


@tool
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

# Create an Ollama model instance
ollama_model = OllamaModel(
    host="http://localhost:11434",  # Ollama server address
    model_id="granite4:3b"               # Specify which model to use
)

# Create an agent using the Ollama model
agent = Agent(
    model=ollama_model,
    tools=[add_numbers]  # Register the add_numbers tool with the agent
)

# Use the agent
agent("1+1はいくつですか？") # Prints model output to stdout by default
