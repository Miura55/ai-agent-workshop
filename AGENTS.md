# Repository Guidelines

## Project Structure & Module Organization

This repository contains the sample code for the [Strands Agents local AI agent workshop](https://zenn.dev/kmiura55/books/local-ai-agent-handson). Python examples live at the repository root: `step1.py` introduces an agent, `step1_2.py` adds a conversation loop, `step2.py` registers a tool, `step3.py` connects to Tavily MCP, and `report_agent.py` provides the Streamlit report-writing app. `main.py` is a small starter file. There is currently no dedicated test or assets directory. Runtime reports go to `reports/`; conversation and local mem0 data go to `sessions/`. Both are ignored by Git.

## Build, Test, and Development Commands

- `uv sync` installs the versions recorded in `uv.lock`.
- `uv run python step1.py` runs the basic local agent; use the corresponding `step2.py` or `step3.py` command for later examples.
- `uv run streamlit run report_agent.py` starts the report app.
- `ollama pull qwen3.5:2b`, `ollama pull gemma4:e2b`, and `ollama pull nomic-embed-text:latest` fetch models used by the examples and local memory.

Keep Ollama available at `http://localhost:11434`. `step3.py` and `report_agent.py` require `TAVILY_API_KEY` in a local `.env` file. Never commit API keys.

## Coding Style & Naming Conventions

Use Python with four-space indentation, `snake_case` for functions and variables, and descriptive module names matching the workshop step. Keep examples direct and consistent with the existing Strands Agents and Ollama patterns. Add runtime dependencies through `uv add <package>` so `pyproject.toml` and `uv.lock` stay in sync. No formatter or linter is configured.

## Testing Guidelines

There is no automated test suite or coverage requirement yet. For a code change, run the smallest relevant example manually when the required Ollama model and environment variables are available, and report any checks you could not run. Do not add a test framework without coordinating the scope of the change.

## Commit & Pull Request Guidelines

Recent history uses short imperative summaries, often with Conventional Commit prefixes such as `feat:` and `refactor:`. Use a concise message, for example `fix: keep bullets unordered in Word output` or `docs: explain workshop setup`. PRs should summarize the user-facing change, list verification performed, and include a screenshot for Streamlit UI changes when useful. Link a related issue when one exists.

## Security & Local Data

Keep `.env`, `reports/`, and `sessions/` out of commits. Web search uses Tavily; mem0 storage is local under `sessions/`. Do not print or expose API keys in logs, examples, or PR descriptions.
