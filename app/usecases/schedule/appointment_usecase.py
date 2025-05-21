import logging
from fastapi import BackgroundTasks
from typing import List, Dict, Any

from app.schemas import AppointmentRequest, AppointmentResponse
from app.infrastructure.graph_api import GraphAPIClient
from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.utils.formatting import parse_candidate, format_candidate_date
from app.config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()

async def create_appointment_usecase(
    background_tasks: BackgroundTasks, appointment_req: AppointmentRequest
) -> AppointmentResponse:
    """面接担当者の予定を登録し、確認メールを送信するユースケース"""
    try:
        if not appointment_req.candidate or appointment_req.candidate.lower() == "none":
            logger.info("候補として '可能な日程がない' が選択されました。予定は登録されません。")
            background_tasks.add_task(send_no_available_schedule_emails, appointment_req)
            return AppointmentResponse(
                message="候補として '可能な日程がない' が選択されました。予定は登録されません。",
                subjects=[],
                meeting_urls=[],
                users=appointment_req.users,
            )

        # 候補日をパースしてイベントを作成・登録
        created_events = _create_and_register_events(appointment_req)

        # 確認メールを送信
        meeting_urls = [e.get("onlineMeeting", {}).get("joinUrl") for e in created_events]
        background_tasks.add_task(send_confirmation_emails, appointment_req, meeting_urls)

        return AppointmentResponse(
            message="予定を登録しました。確認メールは別途送信されます。",
            subjects=[e.get("subject") for e in created_events],
            meeting_urls=meeting_urls,
            users=appointment_req.users,
        )

    except Exception as e:
        logger.error(f"予定作成ユースケースエラー: {e}")
        raise

def _create_and_register_events(appointment_req: AppointmentRequest) -> List[Dict[str, Any]]:
    """候補日をパースしてイベントを作成・登録し、IDを保存"""
    try:
        # 候補日をパース
        start_str, end_str, selected_candidate = parse_candidate(appointment_req.candidate)
        logger.info(f"候補日パース成功: {start_str} - {end_str}")

        # イベントを作成
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

        # イベントを登録
        graph_api_client = GraphAPIClient()
        created_events = []
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

    except Exception as e:
        logger.error(f"イベント作成・登録処理失敗: {e}")
        raise

def send_confirmation_emails(appointment_req: AppointmentRequest, meeting_urls: List[str]) -> None:
    """内部向けおよび先方向けの確認メール送信処理をまとめる。"""
    graph_api_client = GraphAPIClient()
    meeting_url = meeting_urls[0] if isinstance(meeting_urls, list) else meeting_urls
    
    # 内部関係者向けメール送信
    subject = f"【{appointment_req.company}/{appointment_req.lastname}{appointment_req.firstname}様】日程確定"
    body = (
        "日程調整が完了しました。詳細は下記の通りです。<br><br>"
        f"・氏名<br>{appointment_req.lastname} {appointment_req.firstname}<br>"
        f"・所属<br>{appointment_req.company}<br>"
        f"・メールアドレス<br>{appointment_req.email}<br>"
        f"・日程<br>{format_candidate_date(appointment_req.candidate)}<br>"
        f'・会議URL<br><a href="{meeting_url}">{meeting_url}</a><br><br>'
    )
    for to_email in appointment_req.users:
        graph_api_client.send_email(
            config['SYSTEM_SENDER_EMAIL'], 
            to_email, 
            subject, 
            body
        )

    # クライアント向けメール送信
    subject = "日程確定（インテリジェントフォース）"
    reschedule_link = f"{config['API_URL']}/reschedule?token={appointment_req.token}"
    body = (
        f"{appointment_req.lastname}様<br><br>"
        "この度は日程を調整いただきありがとうございます。<br>"
        "ご登録いただいた内容、および当日の会議URLは下記の通りです。<br><br>"
        f"・氏名<br>{appointment_req.lastname} {appointment_req.firstname}<br><br>"
        f"・所属<br>{appointment_req.company}<br><br>"
        f"・メールアドレス<br>{appointment_req.email}<br><br>"
        f"・日程<br>{format_candidate_date(appointment_req.candidate)}<br><br>"
        f"・会議URL<br><a href=\"{meeting_url}\">{meeting_url}</a><br><br>"
        "※日程の再調整が必要な場合はこちらからご対応ください：<br>"
        f"<a href=\"{reschedule_link}\">{reschedule_link}</a><br>"
        "再調整のご対応後は、元の予定は自動的に削除されます。<br><br>"
        "以上になります。<br>"
        "当日はどうぞよろしくお願いいたします。"
    )
    graph_api_client.send_email(
        config['SYSTEM_SENDER_EMAIL'],
        appointment_req.email,
        subject,
        body
    )

def send_no_available_schedule_emails(appointment_req: AppointmentRequest) -> None:
    """可能な日程がない場合のメールを担当者に送信する"""
    graph_api_client = GraphAPIClient()
    subject = f"【{appointment_req.company}/{appointment_req.lastname}{appointment_req.firstname}様】日程確定"
    body = (
        f"{appointment_req.lastname}様<br><br>"
        "以下の候補者から日程調整の回答がありましたが、提示された日程では面接の調整ができませんでした。<br><br>"
        f"・氏名<br>{appointment_req.lastname} {appointment_req.firstname}<br><br>"
        f"・所属<br>{appointment_req.company}<br><br>"
        f"・メールアドレス<br>{appointment_req.email}<br><br>"
        "候補者からは「可能な日程がない」との回答がありました。<br>"
        "別の日程を提示するか、直接候補者と調整をお願いします。<br><br>"
        "※このメールは自動送信されています。"
    )

    for to_email in appointment_req.users:
        graph_api_client.send_email(
            config['SYSTEM_SENDER_EMAIL'],
            to_email,
            subject,
            body
        )
