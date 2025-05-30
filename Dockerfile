# 軽量ベースイメージを使用
FROM python:3.10-slim

# 作業ディレクトリを設定
WORKDIR /schedule_management_api

# システム依存パッケージをインストール（ODBCまわり含む）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    gnupg \
    unixodbc \
    unixodbc-dev \
    libgssapi-krb5-2 \
    libssl-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Microsoft ODBC Driver for SQL Serverを追加
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
    msodbcsql18 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
COPY ./requirements.txt /schedule_management_api/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /schedule_management_api/requirements.txt

# アプリのコードをコピー
COPY ./app /schedule_management_api/app

# Uvicornを使ってFastAPIを起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
