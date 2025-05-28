import logging
from fastapi import BackgroundTasks
from typing import List, Dict, Any, Optional

from app.schemas import AppointmentRequest, AppointmentResponse
from app.infrastructure.graph_api import GraphAPIClient
from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.utils.formatting import parse_candidate, format_candidate_date
from app.config.config import get_config
from app.infrastructure.appointment_repository import AppointmentRepository

logger = logging.getLogger(__name__)

config = get_config()

async def create_appointment_usecase(
    background_tasks: BackgroundTasks,
    appointment_req: AppointmentRequest,
) -> AppointmentResponse:
    """面接担当者の予定を登録し、確認メールを送信するユースケース"""

    try:
        if not appointment_req.schedule_interview_datetime or (
            appointment_req.schedule_interview_datetime.lower() == "none"
        ):
            logger.info("候補として '可能な日程がない' が選択されました。予定は登録されません。")
            background_tasks.add_task(send_no_available_schedule_emails, appointment_req)
            return AppointmentResponse(
                message="候補として '可能な日程がない' が選択されました。予定は登録されません。",
                subjects=[],
                meeting_urls=[],
                employee_email=appointment_req.employee_email,
            )

        created_events = _create_and_register_events(appointment_req)
        if not created_events:
            raise RuntimeError("Graph API がイベントを返しませんでした")

        AppointmentRepository().create_appointment(appointment_req)

        meeting_urls: List[Optional[str]] = [
            (e.get("onlineMeeting") or {}).get("joinUrl") if e else None
            for e in created_events
        ]
        background_tasks.add_task(send_confirmation_emails, appointment_req, meeting_urls)

        return AppointmentResponse(
            message="予定を登録しました。確認メールは別途送信されます。",
            subjects=[e.get("subject") if e else None for e in created_events],
            meeting_urls=meeting_urls,
            employee_email=appointment_req.employee_email,
        )

    except Exception as e:
        logger.exception("予定作成ユースケースエラー: %s", e)
        raise

def _create_and_register_events(appointment_req: AppointmentRequest) -> List[Dict[str, Any]]:
    """候補日をパースしてイベントを作成・登録し、ID を Cosmos DB に保存"""

    if not appointment_req.schedule_interview_datetime:
        raise ValueError("schedule_interview_datetime is required")

    start_str, end_str, _ = parse_candidate(appointment_req.schedule_interview_datetime)
    if not (start_str and end_str):
        raise ValueError(f"Invalid datetime format. start={start_str}, end={end_str}")

    logger.info("候補日パース成功: %s - %s", start_str, end_str)

    event_payload = {
        "subject": f"面接: {appointment_req.candidate_lastname} {appointment_req.candidate_firstname} ({appointment_req.company})",
        "body": {
            "contentType": "HTML",
            "content": f"候補日: {start_str} - {end_str}",
        },
        "start": {"dateTime": start_str, "timeZone": "Tokyo Standard Time"},
        "end": {"dateTime": end_str, "timeZone": "Tokyo Standard Time"},
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness",
    }

    graph_api_client = GraphAPIClient()
    created_events: List[Dict[str, Any]] = []

    try:
        event_resp = graph_api_client.register_event(appointment_req.employee_email, event_payload)
        if not event_resp or "id" not in event_resp:
            raise RuntimeError(f"Graph API returned invalid response: {event_resp}")
        created_events.append(event_resp)
        logger.info("イベント登録成功: %s - %s", appointment_req.employee_email, event_resp["id"])
    except Exception as e:
        logger.exception("イベント登録失敗: %s", e)
        raise

    if not appointment_req.cosmos_db_id:
        logger.warning("cosmos_db_id が無いため CosmosDB の更新をスキップします")
        return created_events

    try:
        event_ids = {appointment_req.employee_email: created_events[0]["id"]}
        AzCosmosDBClient().update_form_with_events(
            appointment_req.cosmos_db_id,
            event_ids,
        )
    except Exception as e:
        logger.exception("Cosmos DB 更新失敗: %s", e)
        # 更新失敗してもイベントは作成済みなので、ここでは例外を再スローせずログのみ残す

    return created_events

def send_confirmation_emails(
    appointment_req: AppointmentRequest,
    meeting_urls: List[Optional[str]],
) -> None:
    graph_api_client = GraphAPIClient()
    meeting_url = next((url for url in meeting_urls if url), None)
    if meeting_url is None:
        raise ValueError("会議 URL が取得できませんでした")

    # 内部向け
    internal_subject = (
        f"【{appointment_req.company}/{appointment_req.candidate_lastname}{appointment_req.candidate_firstname}様】日程確定"
    )
    internal_body = (
        "日程調整が完了しました。詳細は下記の通りです。<br><br>"
        f"・氏名<br>{appointment_req.candidate_lastname} {appointment_req.candidate_firstname}<br>"
        f"・所属<br>{appointment_req.company}<br>"
        f"・メールアドレス<br>{appointment_req.candidate_email}<br>"
        f"・日程<br>{format_candidate_date(appointment_req.schedule_interview_datetime)}<br>"
        f'・会議URL<br><a href="{meeting_url}">{meeting_url}</a><br><br>'
    )
    if appointment_req.employee_email:
        graph_api_client.send_email(
            config["SYSTEM_SENDER_EMAIL"],
            appointment_req.employee_email,
            internal_subject,
            internal_body,
        )

    # クライアント向け
    client_subject = "日程確定（インテリジェントフォース）"
    reschedule_link = (
        f"{config['API_URL']}/reschedule?cosmos_db_id={appointment_req.cosmos_db_id or ''}"
    )
    client_body = (
        f"{appointment_req.candidate_lastname}様<br><br>"
        "この度は日程を調整いただきありがとうございます。<br>"
        "ご登録いただいた内容、および当日の会議URLは下記の通りです。<br><br>"
        f"・氏名<br>{appointment_req.candidate_lastname} {appointment_req.candidate_firstname}<br><br>"
        f"・所属<br>{appointment_req.company}<br><br>"
        f"・メールアドレス<br>{appointment_req.candidate_email}<br><br>"
        f"・日程<br>{format_candidate_date(appointment_req.schedule_interview_datetime)}<br><br>"
        f"・会議URL<br><a href=\"{meeting_url}\">{meeting_url}</a><br><br>"
        "※日程の再調整が必要な場合はこちらからご対応ください：<br>"
        f"<a href=\"{reschedule_link}\">{reschedule_link}</a><br>"
        "再調整のご対応後は、元の予定は自動的に削除されます。<br><br>"
        "以上になります。<br>"
        "当日はどうぞよろしくお願いいたします。"
    )
    graph_api_client.send_email(
        config["SYSTEM_SENDER_EMAIL"],
        appointment_req.candidate_email,
        client_subject,
        client_body,
    )


def send_no_available_schedule_emails(appointment_req: AppointmentRequest) -> None:
    if not appointment_req.employee_email:
        logger.warning("employee_email が無いため通知メールをスキップします")
        return

    graph_api_client = GraphAPIClient()
    subject = (
        f"【{appointment_req.company}/{appointment_req.candidate_lastname}{appointment_req.candidate_firstname}様】日程確定"
    )
    body = (
        f"{appointment_req.candidate_lastname}様<br><br>"
        "以下の候補者から日程調整の回答がありましたが、提示された日程では面接の調整ができませんでした。<br><br>"
        f"・氏名<br>{appointment_req.candidate_lastname} {appointment_req.candidate_firstname}<br><br>"
        f"・所属<br>{appointment_req.company}<br><br>"
        f"・メールアドレス<br>{appointment_req.candidate_email}<br><br>"
        "候補者からは「可能な日程がない」との回答がありました。<br>"
        "別の日程を提示するか、直接候補者と調整をお願いします。<br><br>"
        "※このメールは自動送信されています。"
    )
    graph_api_client.send_email(
        config["SYSTEM_SENDER_EMAIL"],
        appointment_req.employee_email,
        subject,
        body,
    )
