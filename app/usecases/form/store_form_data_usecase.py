import logging
from fastapi import HTTPException
from app.schemas import FormData
from app.infrastructure.az_cosmos import AzCosmosDBClient

logger = logging.getLogger(__name__)

async def store_form_data_usecase(payload: FormData) -> str:
    """
    フォームデータを保存し、トークンを返すユースケース
    """
    try:
        cosmos_db_client = AzCosmosDBClient()
        token = cosmos_db_client.create_form_data(payload.model_dump())
        return token
    except Exception as e:
        logger.error(f"フォームデータの保存に失敗しました: {e}")
        raise HTTPException(status_code=500, detail="Failed to store form data")
