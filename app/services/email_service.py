import logging
from typing import List
from app.config import SYSTEM_SENDER_EMAIL, BACKEND_URL
from app.infrastructure.graph_api import send_email
from app.utils.formatter import format_candidate_date
from app.schemas.form import AppointmentRequest

logger = logging.getLogger(__name__)


def send_confirmation_emails(
    access_token: str, appointment_req: AppointmentRequest, meeting_url: List[str]
) -> None:
    """内部向けおよび先方向けの確認メール送信処理をまとめる。"""
    send_appointment_emails(access_token, appointment_req, meeting_url)
    send_appointment_emails_client(access_token, appointment_req, meeting_url)


def send_appointment_emails(access_token: str, appointment_request: AppointmentRequest, meeting_url: List[str]) -> None:
    """AppointmentRequest オブジェクトの情報を利用して、リクエストに含まれるすべてのユーザーにメールを送信する関数"""
    # meeting_urlがリストの場合、最初の要素を使用して余計なかっこを除去する
    if isinstance(meeting_url, list):
        meeting_url = meeting_url[0]

    # 件名の作成
    subject = f"【{appointment_request.company}/{appointment_request.lastname}{appointment_request.firstname}様】日程確定"

    # 本文の作成
    body = (
        "日程調整が完了しました。詳細は下記の通りです。<br><br>"
        f"・氏名<br>{appointment_request.lastname} {appointment_request.firstname}<br>"
        f"・所属<br>{appointment_request.company}<br>"
        f"・メールアドレス<br>{appointment_request.email}<br>"
        f"・日程<br>{format_candidate_date(appointment_request.candidate)}<br>"
        f'・会議URL<br><a href="{meeting_url}">{meeting_url}</a><br><br>'
    )

    # リスト内の各送信先へメールを送信
    for to_email in appointment_request.users:
        send_email(access_token, SYSTEM_SENDER_EMAIL, to_email, subject, body)


def send_appointment_emails_client(access_token: str, appointment_request: AppointmentRequest, meeting_url: List[str]) -> None:
    """先方向けに、AppointmentRequest オブジェクトの情報を元にメールを送信する関数"""
    # meeting_urlがリストの場合、最初の要素を使用して余計なかっこを除去する
    if isinstance(meeting_url, list):
        meeting_url = meeting_url[0]

    # 件名の作成
    subject = "日程確定（インテリジェントフォース）"

    # 再調整用リンクの作成
    # ※クリック時に元の予定を自動削除する処理が連携される前提
    reschedule_link = f"{BACKEND_URL}/reschedule?token={appointment_request.token}"

    # 本文の作成（HTMLフォーマット）
    body = (
        f"{appointment_request.lastname}様<br><br>"
        "この度は日程を調整いただきありがとうございます。<br>"
        "ご登録いただいた内容、および当日の会議URLは下記の通りです。<br><br>"
        f"・氏名<br>{appointment_request.lastname} {appointment_request.firstname}<br><br>"
        f"・所属<br>{appointment_request.company}<br><br>"
        f"・メールアドレス<br>{appointment_request.email}<br><br>"
        f"・日程<br>{format_candidate_date(appointment_request.candidate)}<br><br>"
        f"・会議URL<br>{meeting_url}<br><br>"
        "※日程の再調整が必要な場合はこちらからご対応ください：<br>"
        f"{reschedule_link}<br>"
        "再調整のご対応後は、元の予定は自動的に削除されます。<br><br>"
        "以上になります。<br>"
        "当日はどうぞよろしくお願いいたします。"
    )

    # リスト内の各送信先へメールを送信
    send_email(
        access_token, SYSTEM_SENDER_EMAIL, appointment_request.email, subject, body
    )


def send_no_available_schedule_emails(access_token: str, appointment_request: AppointmentRequest) -> None:
    """可能な日程がない場合のメールを担当者に送信する関数"""
    # 件名の作成
    subject = f"【{appointment_request.company}/{appointment_request.lastname}{appointment_request.firstname}様】日程調整の回答"

    # 本文の作成（HTMLフォーマット）
    body = (
        f"{appointment_request.lastname}様<br><br>"
        "以下の候補者から日程調整の回答がありましたが、提示された日程では面接の調整ができませんでした。<br><br>"
        f"・氏名<br>{appointment_request.lastname} {appointment_request.firstname}<br><br>"
        f"・所属<br>{appointment_request.company}<br><br>"
        f"・メールアドレス<br>{appointment_request.email}<br><br>"
        "候補者からは「可能な日程がない」との回答がありました。<br>"
        "別の日程を提示するか、直接候補者と調整をお願いします。<br><br>"
        "※このメールは自動送信されています。"
    )

    # リスト内の各送信先へメールを送信
    for to_email in appointment_request.users:
        send_email(access_token, SYSTEM_SENDER_EMAIL, to_email, subject, body)
