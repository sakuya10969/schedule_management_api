import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Body

from app.schemas import (
    ScheduleRequest,
    AppointmentRequest,
    AppointmentResponse,
    AvailabilityResponse,
    RescheduleRequest,
)
from app.infrastructure.employee_directory_repository import EmployeeDirectoryRepository
from app.usecases.schedule.availability_usecase import AvailabilityUsecase
from app.usecases.schedule.appointment_usecase import AppointmentUsecase
from app.usecases.schedule.reschedule_usecase import RescheduleUsecase
from app.usecases.schedule.get_reschedule_data_usecase import GetRescheduleDataUsecase

router = APIRouter(tags=["schedule"])
logger = logging.getLogger(__name__)

@router.get("/employee_directory")
async def get_employee_directory():
    """従業員一覧を取得"""
    try:
        employee_directory_repository = EmployeeDirectoryRepository()
        employee_directory_data_list = employee_directory_repository.get_all_employee_directory()
        return [
            {
                "name": employee_directory_data.name,
                "email": employee_directory_data.mail,
            }
            for employee_directory_data in employee_directory_data_list
        ]
    except Exception as e:
        logger.error(f"従業員一覧取得エラー: {e}")
        raise HTTPException(status_code=500, detail="従業員一覧取得エラー")

@router.post("/availability", response_model=AvailabilityResponse)
async def get_availability(schedule_req: ScheduleRequest):
    """指定されたユーザリストと時間帯における空き時間を返す"""
    try:
        return await AvailabilityUsecase().execute(schedule_req)
    except Exception as e:
        logger.error(f"空き時間取得に失敗: {e}")
        raise HTTPException(status_code=500, detail="空き時間取得エラー")


@router.post("/appointment", response_model=AppointmentResponse)
async def create_appointment(
    background_tasks: BackgroundTasks, appointment_req: AppointmentRequest = Body(...)
):
    """面接担当者の予定を登録し、確認メールを送信"""
    try:
        return await AppointmentUsecase().execute(background_tasks, appointment_req)
    except Exception as e:
        logger.error(f"予定作成エラー: {e}")
        raise HTTPException(status_code=500, detail="予定作成エラー")


@router.get("/reschedule")
async def reschedule(
    cosmos_db_id: str = Query(..., description="CosmosDBのID"),
):
    """日程再調整のための日時を取得"""
    try:
        return await GetRescheduleDataUsecase().execute(cosmos_db_id)
    except Exception as e:
        logger.error(f"リスケジュールエラー: {e}")
        raise HTTPException(status_code=500, detail="リスケジュールエラー")


@router.post("/reschedule")
async def reschedule(
    reschedule_req: RescheduleRequest = Body(...),
):
    """日程再調整の確認および実行"""
    try:
        return await RescheduleUsecase().execute(reschedule_req)
    except Exception as e:
        logger.error(f"リスケジュールエラー: {e}")
        raise HTTPException(status_code=500, detail="リスケジュールエラー")
