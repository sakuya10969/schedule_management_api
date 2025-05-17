import logging
from fastapi import HTTPException

from app.schemas import FormData
from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.utils.time import split_candidates

logger = logging.getLogger(__name__)

async def retrieve_form_data_usecase(token: str) -> FormData:
    """
    フォームデータを取得し、返すユースケース
    """
    try:
        cosmos_db_client = AzCosmosDBClient()
        form_data = cosmos_db_client.get_form_data(token)
        form_data["candidates"] = split_candidates(form_data["candidates"], form_data["duration_minutes"])
        
        return FormData(**form_data)

    except Exception as e:
        logger.error(f"フォームデータが見つかりません: {e}")
        raise HTTPException(status_code=404, detail="Token not found")
