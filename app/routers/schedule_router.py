import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Body
from app.schemas import ScheduleRequest, AppointmentRequest, AppointmentResponse, AvailabilityResponse

# ユースケースのインポート
from app.usecases.schedule.availability_usecase import get_availability_usecase
from app.usecases.schedule.appointment_usecase import create_appointment_usecase
from app.usecases.schedule.reschedule_usecase import reschedule_usecase

router = APIRouter(tags=["schedule"])
logger = logging.getLogger(__name__)

@router.post("/get_availability", response_model=AvailabilityResponse)
async def get_availability(schedule_req: ScheduleRequest):
    """指定されたユーザリストと時間帯における空き時間を返す"""
    try:
        return await get_availability_usecase(schedule_req)
    except Exception as e:
        logger.error(f"空き時間取得に失敗: {e}")
        raise HTTPException(status_code=500, detail="空き時間取得エラー")

@router.post("/appointment", response_model=AppointmentResponse)
async def create_appointment(
    background_tasks: BackgroundTasks, appointment_req: AppointmentRequest = Body(...)
):
    """面接担当者の予定を登録し、確認メールを送信"""
    try:
        return await create_appointment_usecase(background_tasks, appointment_req)
    except Exception as e:
        logger.error(f"予定作成エラー: {e}")
        raise HTTPException(status_code=500, detail="予定作成エラー")

@router.get("/reschedule")
async def reschedule(
    token: str = Query(..., description="フォームのトークン"),
    confirm: bool = Query(False, description="キャンセル処理確認フラグ"),
):
    """日程再調整の確認および実行"""
    try:
        return await reschedule_usecase(token, confirm)
    except Exception as e:
        logger.error(f"リスケジュールエラー: {e}")
        raise HTTPException(status_code=500, detail="リスケジュールエラー")
