# 軽量ベースイメージを使用
FROM python:3.10-slim

# 作業ディレクトリを設定
WORKDIR /schedule_management_api

# 必要なシステム依存パッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
COPY ./requirements.txt /schedule_management_api/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /schedule_management_api/requirements.txt

# アプリのコードをコピー
COPY ./app /schedule_management_api/app

# Uvicornを使ってFastAPIを起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]