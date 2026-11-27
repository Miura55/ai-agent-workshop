# レポート作成代行エージェント

## ローカル会話記憶

会話履歴は `sessions/` に保存します。mem0 OSSの長期記憶もローカルで実行し、Ollamaを記憶の抽出と埋め込みに使います。Mem0 PlatformのAPIキーは不要です。

依存関係を同期した後、Ollamaで埋め込みモデルを取得してください。

```bash
uv sync
ollama pull nomic-embed-text:latest
```

チャットモデルにはアプリ本体と同じ `gemma4:e2b` を使います。Ollamaを `http://localhost:11434` で起動してください。Qdrantのベクトルデータとmem0の履歴DBは、それぞれ `sessions/mem0_qdrant/` と `sessions/mem0_history.db` に保存されます。
