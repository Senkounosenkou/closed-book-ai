# 1. ベースにするイメージ
FROM python:3.11-slim

# 2. コンテナ内の作業場所
WORKDIR /app

# --- 設定ファイルと、さっき作ったリストをコピー ---
COPY .streamlit /app/.streamlit
COPY requirements.txt .

# 3. 必要なライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# 4. コンテナ起動コマンド
CMD ["streamlit", "run", "main.py", "--server.address", "0.0.0.0"]
