import logging
from fastapi.responses import RedirectResponse, HTMLResponse
from app.infrastructure.graph_api import (
    get_user_schedules,
    register_event,
    send_email,
)
from app.utils.access_token import get_access_token
from app.utils.time import time_string_to_float, slot_to_time, find_common_availability
from app.schemas import ScheduleRequest, AppointmentRequest, AvailabilityResponse, AppointmentResponse
from app.config import FRONTEND_URL, API_URL

logger = logging.getLogger(__name__)

async def get_availability_usecase(schedule_req: ScheduleRequest):
    """ユーザーの空き時間を取得"""
    access_token = get_access_token()
    schedule_info = get_user_schedules(
        access_token,
        schedule_req.users[0].email,
        f"{schedule_req.start_date}T{schedule_req.start_time}:00",
        f"{schedule_req.end_date}T{schedule_req.end_time}:00",
        schedule_req.time_zone,
        [user.email for user in schedule_req.users],
    )
    start_hour = await time_string_to_float(schedule_req.start_time)
    end_hour = await time_string_to_float(schedule_req.end_time)
    free_slots_list = find_common_availability(schedule_info, start_hour, end_hour)

    common_times = [
        [slot_to_time(schedule_req.start_date, slot)]
        for slot in free_slots_list
    ]
    return AvailabilityResponse(common_availability=common_times)

async def create_appointment_usecase(appointment_req: AppointmentRequest, background_tasks):
    """面接担当者の予定表にイベントを登録"""
    access_token = get_access_token()
    event = {
        "subject": f"【{appointment_req.company}/{appointment_req.lastname}様】日程確定",
        "start": {"dateTime": appointment_req.start_time, "timeZone": "Tokyo Standard Time"},
        "end": {"dateTime": appointment_req.end_time, "timeZone": "Tokyo Standard Time"},
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness",
    }

    created_events = []
    for user_email in appointment_req.users:
        result = register_event(access_token, user_email, event)
        created_events.append(result)

    subjects = [event.get("subject") for event in created_events]
    meeting_urls = [event.get("onlineMeeting", {}).get("joinUrl") for event in created_events]

    return AppointmentResponse(
        message="予定を登録しました",
        subjects=subjects,
        meeting_urls=meeting_urls,
        users=appointment_req.users,
    )

async def reschedule_usecase(token: str, confirm: bool):
    """日程再調整の処理"""
    if not confirm:
        redirect_url = f"{FRONTEND_URL}/appointment?token={token}"
        return RedirectResponse(url=redirect_url, status_code=302)
    
    html_content = f"""
    <html>
    <head>
        <title>再調整完了</title>
    </head>
    <body>
        <p>予定がキャンセルされました。</p>
        <a href="{FRONTEND_URL}/appointment?token={token}">再調整画面へ</a>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)
