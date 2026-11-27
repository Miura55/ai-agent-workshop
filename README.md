# Strands Agents ローカルAIエージェント ハンズオン

このリポジトリは、Zennの書籍「[Strands AgentsでローカルAIエージェント開発ハンズオン](https://zenn.dev/kmiura55/books/local-ai-agent-handson)」で使用するサンプルコードです。Ollamaで動かすローカルLLMをStrands Agentsから呼び出し、ツール、MCP、レポート作成へと段階的に発展させます。

## ハンズオンの構成

| 書籍の内容 | サンプルコード | 学ぶこと |
| --- | --- | --- |
| Step 1: AIエージェントを開発する | [`step1.py`](step1.py) | OllamaのLLMをStrands Agentsから呼び出す |
| Step 1: 会話を続ける | [`step1_2.py`](step1_2.py) | 対話ループと会話履歴の管理 |
| Step 2: ツールを呼び出す | [`step2.py`](step2.py) | `@tool`で現在時刻取得ツールを追加する |
| Step 3: MCPを呼び出す | [`step3.py`](step3.py) | TavilyのMCPサーバーと連携してWeb検索する |
| Step 4: レポートエージェントを作成する | [`report_agent.py`](report_agent.py) | StreamlitのチャットUI、Web検索、Word出力を組み合わせる |

## 必要なもの

- Python 3.13以上
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) と、モデルを実行できるPC環境
- Tavily APIキー（`step3.py` と `report_agent.py` を使う場合）

## セットアップ

リポジトリのルートで依存パッケージをインストールします。

```bash
uv sync
```

このサンプルが使用するモデルをOllamaで取得します。

```bash
ollama pull qwen3.5:2b
ollama pull gemma4:e2b
ollama pull nomic-embed-text:latest
```

Ollamaを起動し、`http://localhost:11434` で利用できるようにしてください。Ollamaのモデル一覧は `ollama list` で確認できます。

### Tavilyの設定

`step3.py` と `report_agent.py` はTavilyのMCPサーバーを使います。TavilyでAPIキーを取得し、リポジトリのルートに `.env` ファイルを作成します。

```dotenv
TAVILY_API_KEY=取得したAPIキー
```

`.env` はGit管理対象外です。APIキーをソースコードやコミットに含めないでください。

## 実行方法

### Step 1: エージェントを実行

```bash
uv run python step1.py
```

継続して会話する例を実行するには、次のコマンドを使います。終了時は `exit` または `quit` を入力します。

```bash
uv run python step1_2.py
```

### Step 2: ツールを使うエージェント

```bash
uv run python step2.py
```

### Step 3: MCPでWeb検索

`.env` にTavily APIキーを設定してから実行します。

```bash
uv run python step3.py
```

### Step 4: レポートエージェント

```bash
uv run streamlit run report_agent.py
```

ブラウザーでStreamlitが表示するURLを開きます。チャットで依頼すると、Web検索を使って日本語のレポートを作成できます。DOCXファイルは `reports/` に保存されます。

## セッションとローカルメモリ

`report_agent.py` では、サイドバーから会話セッションの作成、切り替え、名前変更、削除ができます。会話履歴は `sessions/` に保存されます。

mem0 OSSはローカルで動作し、Ollamaで記憶の抽出と埋め込みを行います。Qdrantのベクトルデータとmem0の履歴DBは、それぞれ `sessions/mem0_qdrant/` と `sessions/mem0_history.db` に保存されます。追加のAPIキーは不要です。初回利用時にはOllamaが指定モデルを利用できることを確認してください。

会話データ、mem0データ、生成レポートはローカルに保存され、Git管理対象外です。

## ハンズオン資料

手順や解説は[Zennの書籍](https://zenn.dev/kmiura55/books/local-ai-agent-handson)を参照してください。
