# Pythonイメージ
FROM python:3.10-slim

# 作業ディレクトリを設定
WORKDIR /schedule_management_api

# システム依存パッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    gnupg \
    libssl-dev \
    libgssapi-krb5-2 \
    unixodbc \
    unixodbc-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Microsoft ODBC Driver の追加
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && apt-get purge -y libodbc2 libodbcinst2 unixodbc-common || true && \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
    msodbcsql18 \
    unixodbc \
    unixodbc-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# requirements.txt を最初にコピー
COPY requirements.txt ./requirements.txt

# Pythonパッケージのインストール
RUN pip install --no-cache-dir --upgrade -r requirements.txt || (echo 'pip install failed' && exit 1)

# アプリケーションコードをコピー
COPY ./app /schedule_management_api/app

# モジュール参照エラー対策（PYTHONPATH指定）
ENV PYTHONPATH=/schedule_management_api

# アプリケーション起動（FastAPI + Uvicorn）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
