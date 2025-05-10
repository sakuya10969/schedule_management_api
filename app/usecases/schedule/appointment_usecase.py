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
        if not _has_valid_candidate(appointment_req.candidate):
            return _handle_no_available_schedule(background_tasks, appointment_req)

        start_str, end_str, selected_candidate = _parse_candidate_date(appointment_req.candidate)
        event = _create_event_payload(appointment_req, start_str, end_str)
        created_events = _register_events(appointment_req.users, event)
        
        _store_event_ids(appointment_req.token, created_events, appointment_req.users)
        _schedule_confirmation_emails(background_tasks, appointment_req, created_events)

        return _create_response(created_events, appointment_req.users)

    except Exception as e:
        logger.error(f"予定作成ユースケースエラー: {e}")
        raise

def _has_valid_candidate(candidate: str) -> bool:
    """候補日が有効かどうかを判定"""
    return candidate and candidate.lower() != "none"

def _handle_no_available_schedule(
    background_tasks: BackgroundTasks, appointment_req: AppointmentRequest
) -> AppointmentResponse:
    """候補日がない場合の処理"""
    logger.info("候補として '可能な日程がない' が選択されました。予定は登録されません。")
    email_service = EmailService()
    background_tasks.add_task(email_service.send_no_available_schedule_emails, appointment_req)
    return AppointmentResponse(
        message="候補として '可能な日程がない' が選択されました。予定は登録されません。",
        subjects=[],
        meeting_urls=[],
        users=appointment_req.users,
    )

def _parse_candidate_date(candidate: str) -> tuple:
    """候補日をパース"""
    try:
        start_str, end_str, selected_candidate = parse_candidate(candidate)
        logger.info(f"候補日パース成功: {start_str} - {end_str}")
        return start_str, end_str, selected_candidate
    except Exception as e:
        logger.error(f"候補日パース失敗: {e}")
        raise

def _create_event_payload(appointment_req: AppointmentRequest, start_str: str, end_str: str) -> dict:
    """イベントペイロードを作成"""
    return {
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

def _register_events(users: list, event: dict) -> list:
    """各ユーザーのカレンダーに予定を登録"""
    graph_api_client = GraphAPIClient()
    created_events = []

    for user_email in users:
        try:
            event_resp = graph_api_client.register_event(user_email, event)
            created_events.append(event_resp)
            logger.info(f"イベント登録成功: {user_email} - {event_resp.get('id')}")
        except Exception as e:
            logger.error(f"イベント登録失敗: {user_email} - {e}")

    return created_events

def _store_event_ids(token: str, created_events: list, users: list) -> None:
    """イベントIDをCosmos DBに保存"""
    event_ids = {
        user_email: event.get("id")
        for user_email, event in zip(users, created_events)
        if event.get("id")
    }
    cosmos_db_client = AzCosmosDBClient()
    cosmos_db_client.update_form_with_events(token, event_ids)

def _schedule_confirmation_emails(
    background_tasks: BackgroundTasks, appointment_req: AppointmentRequest, created_events: list
) -> None:
    """確認メールの送信をスケジュール"""
    meeting_urls = [e.get("onlineMeeting", {}).get("joinUrl") for e in created_events]
    email_service = EmailService()
    background_tasks.add_task(email_service.send_confirmation_emails, appointment_req, meeting_urls)

def _create_response(created_events: list, users: list) -> AppointmentResponse:
    """レスポンスを作成"""
    return AppointmentResponse(
        message="予定を登録しました。確認メールは別途送信されます。",
        subjects=[e.get("subject") for e in created_events],
        meeting_urls=[e.get("onlineMeeting", {}).get("joinUrl") for e in created_events],
        users=users,
    )
