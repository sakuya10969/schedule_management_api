import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Body
from app.usecases.schedule_usecase import (
    get_availability_usecase,
    create_appointment_usecase,
    reschedule_usecase,
)
from app.schemas import ScheduleRequest, AppointmentRequest, AvailabilityResponse, AppointmentResponse

router = APIRouter(tags=["schedule"])
logger = logging.getLogger(__name__)

@router.post("/get_availability", response_model=AvailabilityResponse)
async def get_availability(schedule_req: ScheduleRequest):
    """指定されたユーザリストと日付・時間帯における空き時間候補を返す"""
    try:
        result = await get_availability_usecase(schedule_req)
        return result
    except Exception as e:
        logger.error(f"候補日の取得に失敗しました: {e}")
        raise HTTPException(status_code=500, detail="候補日の取得に失敗しました")

@router.post("/appointment", response_model=AppointmentResponse)
async def create_appointment(background_tasks: BackgroundTasks, appointment_req: AppointmentRequest = Body(...)):
    """面接担当者の予定表に予定を登録する"""
    try:
        result = await create_appointment_usecase(appointment_req, background_tasks)
        return result
    except Exception as e:
        logger.error(f"予定作成エラー: {str(e)}")
        raise HTTPException(status_code=500, detail="予定作成中にエラーが発生しました")

@router.get("/reschedule")
async def reschedule(token: str = Query(...), confirm: bool = Query(False)):
    """日程の再調整リンクを処理"""
    try:
        result = await reschedule_usecase(token, confirm)
        return result
    except Exception as e:
        logger.error(f"リスケジュールエラー: {str(e)}")
        raise HTTPException(status_code=500, detail="リスケジュール中にエラーが発生しました")
