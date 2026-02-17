⚡ Closed-Book
Local LLM (Ollama) を活用した、プライバシー重視のドキュメント解析プラットフォームです。

🚀 主な機能
ドキュメント参照型QA (RAG): アップロードしたPDFやテキストに基づき、AIが正確に回答します。
資料間矛盾チェック: 複数の資料を比較し、数値や手順の食い違いを自動で指摘します。
マルチユーザー管理: ユーザーごとに独立したストレージを持ち、自分専用の解析環境を構築できます。
完全ローカル運用: データは外部に流出せず、Dockerコンテナ内で完結します。
このイメージを実行するには、ローカルに Ollama が必要です。

リポジトリをクローンまたは設定ファイルを準備
docker-compose.yml を実行
🛠️ クイックスタート (GPU推奨)
以下の docker-compose.yml を使用することで、アプリとAIエンジン(Ollama)をセットで起動できます。

services:
  # 1. 解析アプリ
  app:
    image: senkounosenkou/closed-book-ai:v1.0
    ports:
      - "8501:8501"
    volumes:
      - ./data:/data
      - ./storage:/app/storage
      - ./config.yaml:/app/config.yaml
    depends_on:
      - ollama

  # 2. AIエンジン (Ollama)
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - OLLAMA_HOST=0.0.0.0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  ollama_data:
アクセス: http://localhost:8501

初回ログイン用: admin / 123
