import logging
import urllib.parse
from fastapi.responses import HTMLResponse, RedirectResponse
from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.infrastructure.graph_api import GraphAPIClient
from app.config import FRONTEND_URL, BACKEND_URL

logger = logging.getLogger(__name__)

async def reschedule_usecase(token: str, confirm: bool) -> HTMLResponse:
    """
    リスケジュール処理（キャンセルと確認）
    """
    try:
        # Cosmos DB からフォームデータを取得
        cosmos_db_client = AzCosmosDBClient()
        form = cosmos_db_client.get_form_data(token)

        # イベントIDが存在しない場合はリダイレクト
        if "event_ids" not in form:
            redirect_url = f"{FRONTEND_URL}/appointment?token={token}"
            return RedirectResponse(url=redirect_url, status_code=302)

        # キャンセル確認画面を表示
        if not confirm:
            return generate_confirmation_html(token)

        # イベント削除処理
        graph_api_client = GraphAPIClient()
        event_ids = form["event_ids"]

        for user_email, event_id in event_ids.items():
            try:
                graph_api_client.delete_event(user_email, event_id)
                logger.info(f"予定削除成功: {user_email} - {event_id}")
            except Exception as e:
                logger.error(f"予定削除失敗: {user_email} - {event_id}: {e}")
                raise

        # フォームをリセット（再利用可能にする）
        form["isConfirmed"] = False
        form.pop("event_ids", None)
        cosmos_db_client.update_form_with_events(token, form)

        # キャンセル完了画面の表示
        return generate_reschedule_complete_html(token)

    except Exception as e:
        logger.error(f"リスケジュールユースケースエラー: {e}")
        raise

def generate_confirmation_html(token: str) -> HTMLResponse:
    """
    キャンセル確認用のHTMLレスポンスを生成
    """
    confirm_url = f"{BACKEND_URL}/reschedule?token={token}&confirm=true"
    cancel_url = f"{FRONTEND_URL}/appointment?token={token}"
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>日程再調整の確認</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 flex items-center justify-center min-h-screen">
        <div class="bg-white shadow-xl rounded-lg p-12 max-w-xl text-center">
            <h1 class="text-3xl font-bold mb-6">日程再調整の確認</h1>
            <p class="mb-8 text-lg">既存の予定を削除して再調整しますか？</p>
            <div class="flex justify-center space-x-6">
                <a href="{confirm_url}" class="inline-block bg-red-500 hover:bg-red-700 text-white font-bold py-3 px-6 rounded text-xl">再調整する</a>
                <a href="{cancel_url}" class="inline-block bg-gray-500 hover:bg-gray-700 text-white font-bold py-3 px-6 rounded text-xl">キャンセル</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

def generate_reschedule_complete_html(token: str) -> HTMLResponse:
    """
    リスケジュール完了後のHTMLレスポンスを生成
    """
    link = f"{FRONTEND_URL}/appointment?token={token}"
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>再調整完了</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 flex items-center justify-center min-h-screen">
        <div class="bg-white shadow-xl rounded-lg p-12 max-w-xl text-center">
            <h1 class="text-3xl font-bold mb-6">キャンセル処理完了</h1>
            <p class="mb-8 text-lg">既存の予定は削除されました。<br>以下のボタンから新たに日程をご入力ください。</p>
            <a href="{link}" class="inline-block bg-blue-500 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded text-xl">日程再調整画面へ</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)
