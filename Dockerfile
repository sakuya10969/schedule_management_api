# Debian 12 (bookworm) に固定
FROM python:3.10-slim-bookworm

WORKDIR /schedule_management_api

# 必要パッケージ
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg2 ca-certificates \
    build-essential gcc \
    libssl-dev libgssapi-krb5-2 \
    unixodbc unixodbc-dev \
 && rm -rf /var/lib/apt/lists/*

# Microsoft の鍵とリポジトリ設定
RUN set -eux; \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
      | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg; \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
      > /etc/apt/sources.list.d/microsoft-prod.list; \
    apt-get update; \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18; \
    rm -rf /var/lib/apt/lists/*

# 依存パッケージ
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# アプリケーションコード
COPY ./app /schedule_management_api/app
ENV PYTHONPATH=/schedule_management_api

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
