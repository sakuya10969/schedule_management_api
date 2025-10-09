import logging
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from typing import Any

from app.schemas import FormData
from app.usecases.form.store_form_data_usecase import StoreFormDataUsecase
from app.usecases.form.retrieve_form_data_usecase import RetrieveFormDataUsecase

router = APIRouter(tags=["forms"])
logger = logging.getLogger(__name__)


@router.post("/store_form_data", response_model=dict[str, Any])
async def store_form_data(payload: FormData = Body(...)):
    """
    フォームデータを保存し、CosmosDBのIDを返すエンドポイント
    """
    try:
        cosmos_db_id = await StoreFormDataUsecase().execute(payload)
        return JSONResponse(content={"cosmos_db_id": cosmos_db_id})
    except Exception as e:
        logger.error(f"フォームデータの保存に失敗しました: {e}")
        raise HTTPException(status_code=500, detail="Failed to store form data")


@router.get("/retrieve_form_data", response_model=FormData)
async def retrieve_form_data(
    cosmos_db_id: str = Query(..., description="CosmosDBのID")
):
    """
    CosmosDBのIDから保存されたフォームデータを復元し、空き時間を含めて返すエンドポイント
    """
    try:
        form_data = await RetrieveFormDataUsecase().execute(cosmos_db_id)
        return form_data
    except Exception as e:
        logger.error(f"フォームデータの取得に失敗しました: {e}")
        raise HTTPException(status_code=404, detail="CosmosDB ID not found")
