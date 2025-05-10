import logging
from fastapi import BackgroundTasks

from app.schemas import AppointmentRequest, AppointmentResponse
from app.infrastructure.graph_api import GraphAPIClient
from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.services.email_service import EmailService
from app.utils.formatter import parse_candidate

logger = logging.getLogger(__name__)

async def create_appointment_usecase(
    background_tasks: BackgroundTasks, appointment_req: AppointmentRequest
) -> AppointmentResponse:
    """面接担当者の予定を登録し、確認メールを送信するユースケース"""
    try:
        if not appointment_req.candidate or appointment_req.candidate.lower() == "none":
            logger.info("候補として '可能な日程がない' が選択されました。予定は登録されません。")
            email_service = EmailService()
            background_tasks.add_task(email_service.send_no_available_schedule_emails, appointment_req)
            return AppointmentResponse(
                message="候補として '可能な日程がない' が選択されました。予定は登録されません。",
                subjects=[],
                meeting_urls=[],
                users=appointment_req.users,
            )

        # 候補日をパースしてイベントを作成
        start_str, end_str, selected_candidate = _parse_and_create_event(appointment_req)
        event = {
            "subject": f"面接: {appointment_req.lastname} {appointment_req.firstname}",
            "body": {
                "contentType": "HTML",
                "content": f"候補日: {start_str} - {end_str}"
            },
            "start": {"dateTime": start_str, "timeZone": "Tokyo Standard Time"},
            "end": {"dateTime": end_str, "timeZone": "Tokyo Standard Time"},
            "isOnlineMeeting": True,
            "onlineMeetingProvider": "teamsForBusiness",
        }

        # イベントを登録し、IDを保存
        created_events = _register_and_store_events(appointment_req, event)

        # 確認メールを送信
        meeting_urls = [e.get("onlineMeeting", {}).get("joinUrl") for e in created_events]
        email_service = EmailService()
        background_tasks.add_task(email_service.send_confirmation_emails, appointment_req, meeting_urls)

        return AppointmentResponse(
            message="予定を登録しました。確認メールは別途送信されます。",
            subjects=[e.get("subject") for e in created_events],
            meeting_urls=meeting_urls,
            users=appointment_req.users,
        )

    except Exception as e:
        logger.error(f"予定作成ユースケースエラー: {e}")
        raise

def _parse_and_create_event(appointment_req: AppointmentRequest) -> tuple:
    """候補日をパースしてイベントを作成"""
    try:
        start_str, end_str, selected_candidate = parse_candidate(appointment_req.candidate)
        logger.info(f"候補日パース成功: {start_str} - {end_str}")
        return start_str, end_str, selected_candidate
    except Exception as e:
        logger.error(f"候補日パース失敗: {e}")
        raise

def _register_and_store_events(appointment_req: AppointmentRequest, event: dict) -> list:
    """イベントを登録し、IDを保存"""
    graph_api_client = GraphAPIClient()
    created_events = []

    # イベントを登録
    for user_email in appointment_req.users:
        try:
            event_resp = graph_api_client.register_event(user_email, event)
            created_events.append(event_resp)
            logger.info(f"イベント登録成功: {user_email} - {event_resp.get('id')}")
        except Exception as e:
            logger.error(f"イベント登録失敗: {user_email} - {e}")

    # イベントIDを保存
    event_ids = {
        user_email: event.get("id")
        for user_email, event in zip(appointment_req.users, created_events)
        if event.get("id")
    }
    cosmos_db_client = AzCosmosDBClient()
    cosmos_db_client.update_form_with_events(appointment_req.token, event_ids)

    return created_events
