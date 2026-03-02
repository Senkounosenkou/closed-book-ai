<<<<<<< HEAD
# ⚡ Closed-Book AI (Local RAG Platform)

Local LLM (Ollama) を活用した、プライバシー重視のドキュメント解析プラットフォームです。
本プロジェクトは、**「AI推論エンジン (Ollama)」** と **「解析アプリ (Streamlit)」** を分離して管理する疎結合なインフラ構成を採用しています。

---

## 🛠️ セットアップ手順

本リポジトリをクローンした後、以下の2ステップで環境を構築します。

### 1. 推論エンジン (Ollama) の準備
モデルデータの永続化とパフォーマンス向上のため、Dockerの名前付きボリュームを利用します。

```bash
# 1. データ保存用の領域（ボリューム）を事前に作成
docker volume create ollama_ollama

# 2. Ollama専用の設定ディレクトリへ移動
cd ollama

# 3. AIエンジンを起動（ollama_default ネットワークが自動生成されます）
docker-compose up -d

# 4. ルートディレクトリに戻る
cd ..


###2. 解析アプリ (Closed-Book) の起動
次に、アプリ本体を起動します。アプリは外部ネットワークを通じて自動的にエンジンへ接続します。

Bash
# ルートディレクトリで実行
docker-compose up -d

##🚀 アクセスと初期設定
URL: http://localhost:8501

初期ユーザー: admin

初期パスワード: 123

[!IMPORTANT]
セキュリティに関する注意
初回ログイン後、サイドバーの設定メニューから必ずパスワードを自身のものに変更してください。本アプリはローカル運用を想定していますが、適切なパスワード管理を推奨します。

##📋 動作要件
Docker / Docker Compose

NVIDIA GPU (推奨)

NVIDIA Container Toolkit (GPU利用時)
=======
🛠️ セットアップ手順

このシステムは「解析アプリ」と「AIエンジン(Ollama)」を分離して管理しています。

1. AIエンジン (Ollama) の準備
既存の Ollama 環境を使用するか、ネットワーク名 `ollama_default` で Ollama を起動しておいてください。

2. アプリの起動
リポジトリをクローンし、以下のコマンドで起動します。
$ docker-compose up -d

アクセス: http://localhost:8501
初回ログイン用: admin / 123（※利用開始後に必ず変更してください）
>>>>>>> 5de05cfd0f490170d3d324e48ba6c57c0ff6619d
