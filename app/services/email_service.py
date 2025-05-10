import logging
from typing import List
from app.config import SYSTEM_SENDER_EMAIL, BACKEND_URL
from app.infrastructure.graph_api import send_email
from app.utils.formatter import format_candidate_date
from app.schemas.form import AppointmentRequest

logger = logging.getLogger(__name__)


def send_confirmation_emails(
    access_token: str, appointment_req: AppointmentRequest, meeting_urls: List[str]
) -> None:
    """内部向けおよび先方向けの確認メール送信処理をまとめる。"""
    meeting_url = meeting_urls[0] if isinstance(meeting_urls, list) else meeting_urls
    _send_internal_confirmation_email(access_token, appointment_req, meeting_url)
    _send_client_confirmation_email(access_token, appointment_req, meeting_url)


def _send_internal_confirmation_email(
    access_token: str, appointment_req: AppointmentRequest, meeting_url: str
) -> None:
    """内部関係者向けに確認メールを送信する"""
    subject = _create_internal_subject(appointment_req)
    body = _create_internal_body(appointment_req, meeting_url)

    for to_email in appointment_req.users:
        send_email(access_token, SYSTEM_SENDER_EMAIL, to_email, subject, body)


def _send_client_confirmation_email(
    access_token: str, appointment_req: AppointmentRequest, meeting_url: str
) -> None:
    """クライアント向けに確認メールを送信する"""
    subject = "日程確定（インテリジェントフォース）"
    body = _create_client_body(appointment_req, meeting_url)
    
    send_email(
        access_token, SYSTEM_SENDER_EMAIL, appointment_req.email, subject, body
    )


def send_no_available_schedule_emails(
    access_token: str, appointment_req: AppointmentRequest
) -> None:
    """可能な日程がない場合のメールを担当者に送信する"""
    subject = _create_internal_subject(appointment_req)
    body = _create_no_schedule_body(appointment_req)

    for to_email in appointment_req.users:
        send_email(access_token, SYSTEM_SENDER_EMAIL, to_email, subject, body)


def _create_internal_subject(appointment_req: AppointmentRequest) -> str:
    """内部向けメールの件名を作成"""
    return f"【{appointment_req.company}/{appointment_req.lastname}{appointment_req.firstname}様】日程確定"


def _create_internal_body(appointment_req: AppointmentRequest, meeting_url: str) -> str:
    """内部向けメールの本文を作成"""
    return (
        "日程調整が完了しました。詳細は下記の通りです。<br><br>"
        f"・氏名<br>{appointment_req.lastname} {appointment_req.firstname}<br>"
        f"・所属<br>{appointment_req.company}<br>"
        f"・メールアドレス<br>{appointment_req.email}<br>"
        f"・日程<br>{format_candidate_date(appointment_req.candidate)}<br>"
        f'・会議URL<br><a href="{meeting_url}">{meeting_url}</a><br><br>'
    )


def _create_client_body(appointment_req: AppointmentRequest, meeting_url: str) -> str:
    """クライアント向けメールの本文を作成"""
    reschedule_link = f"{BACKEND_URL}/reschedule?token={appointment_req.token}"
    
    return (
        f"{appointment_req.lastname}様<br><br>"
        "この度は日程を調整いただきありがとうございます。<br>"
        "ご登録いただいた内容、および当日の会議URLは下記の通りです。<br><br>"
        f"・氏名<br>{appointment_req.lastname} {appointment_req.firstname}<br><br>"
        f"・所属<br>{appointment_req.company}<br><br>"
        f"・メールアドレス<br>{appointment_req.email}<br><br>"
        f"・日程<br>{format_candidate_date(appointment_req.candidate)}<br><br>"
        f"・会議URL<br>{meeting_url}<br><br>"
        "※日程の再調整が必要な場合はこちらからご対応ください：<br>"
        f"{reschedule_link}<br>"
        "再調整のご対応後は、元の予定は自動的に削除されます。<br><br>"
        "以上になります。<br>"
        "当日はどうぞよろしくお願いいたします。"
    )


def _create_no_schedule_body(appointment_req: AppointmentRequest) -> str:
    """日程調整不可の場合のメール本文を作成"""
    return (
        f"{appointment_req.lastname}様<br><br>"
        "以下の候補者から日程調整の回答がありましたが、提示された日程では面接の調整ができませんでした。<br><br>"
        f"・氏名<br>{appointment_req.lastname} {appointment_req.firstname}<br><br>"
        f"・所属<br>{appointment_req.company}<br><br>"
        f"・メールアドレス<br>{appointment_req.email}<br><br>"
        "候補者からは「可能な日程がない」との回答がありました。<br>"
        "別の日程を提示するか、直接候補者と調整をお願いします。<br><br>"
        "※このメールは自動送信されています。"
    )
