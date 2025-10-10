import os
from dotenv import load_dotenv
from functools import lru_cache

# .envファイルをロード
load_dotenv()
# Azure Cosmos DB 関連
AZ_COSMOS_DB_KEY = os.getenv("AZ_COSMOS_DB_KEY")
AZ_COSMOS_DB_ENDPOINT = os.getenv("AZ_COSMOS_DB_ENDPOINT")
AZ_COSMOS_DB_NAME = "FormDataDB"
AZ_COSMOS_DB_CONTAINER_NAME = "FormDataContainer"
AZ_COSMOS_DB_PARTITION_KEY = "FormData"
# Azure SQL DB 関連
AZ_SQL_DB_CONNECTION_STRING = os.getenv("AZ_SQL_DB_CONNECTION_STRING")
# Azure AD認証関連
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# Graph API エンドポイント
GRAPH_API_BASE_URL = "https://graph.microsoft.com/v1.0/"
GRAPH_API_BETA_URL = "https://graph.microsoft.com/beta/"
# フロントエンドURL
CLIENT_URL = os.getenv("CLIENT_URL") or "http://localhost:3000"
# バックエンドURL
API_URL = "http://127.0.0.1:8000"
# システム送信者メールアドレス
SYSTEM_SENDER_EMAIL = "crawler01@intelligentforce.co.jp"


@lru_cache()
def get_config():
    return {
        "AZ_COSMOS_DB_KEY": AZ_COSMOS_DB_KEY,
        "AZ_COSMOS_DB_ENDPOINT": AZ_COSMOS_DB_ENDPOINT,
        "AZ_COSMOS_DB_NAME": AZ_COSMOS_DB_NAME,
        "AZ_COSMOS_DB_CONTAINER_NAME": AZ_COSMOS_DB_CONTAINER_NAME,
        "AZ_COSMOS_DB_PARTITION_KEY": AZ_COSMOS_DB_PARTITION_KEY,
        "AZ_SQL_DB_CONNECTION_STRING": AZ_SQL_DB_CONNECTION_STRING,
        "TENANT_ID": TENANT_ID,
        "CLIENT_ID": CLIENT_ID,
        "CLIENT_SECRET": CLIENT_SECRET,
        "GRAPH_API_BASE_URL": GRAPH_API_BASE_URL,
        "GRAPH_API_BETA_URL": GRAPH_API_BETA_URL,
        "CLIENT_URL": CLIENT_URL,
        "API_URL": API_URL,
        "SYSTEM_SENDER_EMAIL": SYSTEM_SENDER_EMAIL,
    }
