import logging
from fastapi.responses import HTMLResponse, RedirectResponse

from app.infrastructure.az_cosmos import AzCosmosDBClient
from app.infrastructure.graph_api import GraphAPIClient
from app.config.config import get_config

logger = logging.getLogger(__name__)

config = get_config()

async def reschedule_usecase(cosmos_db_id: str, confirm: bool) -> HTMLResponse:
    """リスケジュール処理（キャンセルと確認）を行うユースケース"""
    try:
        cosmos_db_client = AzCosmosDBClient()
        form = cosmos_db_client.get_form_data(cosmos_db_id)
        
        if "event_ids" not in form:
            redirect_url = f"{config['CLIENT_URL']}/appointment?cosmosDbId={cosmos_db_id}"
            return RedirectResponse(url=redirect_url, status_code=302)

        if not confirm:
            return _show_confirmation_page(cosmos_db_id)

        # イベントの削除
        graph_api_client = GraphAPIClient()
        for user_email, event_id in form["event_ids"].items():
            try:
                graph_api_client.delete_event(user_email, event_id)
                logger.info(f"予定削除成功: {user_email} - {event_id}")
            except Exception as e:
                logger.error(f"予定削除失敗: {user_email} - {event_id}: {e}")
                raise

        # フォームのリセット
        form["is_confirmed"] = False
        form.pop("event_ids", None)
        cosmos_db_client.update_form_with_events(cosmos_db_id, form)

        return _show_complete_page(cosmos_db_id)

    except Exception as e:
        logger.error(f"リスケジュールユースケースエラー: {e}")
        raise

def _show_confirmation_page(cosmos_db_id: str) -> HTMLResponse:
    """確認ページを表示"""
    return _generate_html(
        cosmos_db_id,
        "日程再調整の確認",
        "既存の予定を削除して再調整しますか？",
        [
            {
                "url": f"{config['API_URL']}/reschedule?cosmos_db_id={cosmos_db_id}&confirm=true",
                "text": "再調整する",
                "class": "bg-red-500 hover:bg-red-700"
            },
            {
                "url": f"{config['CLIENT_URL']}/appointment?cosmos_db_id={cosmos_db_id}",
                "text": "キャンセル",
                "class": "bg-gray-500 hover:bg-gray-700"
            }
        ]
    )

def _show_complete_page(cosmos_db_id: str) -> HTMLResponse:
    """完了ページを表示"""
    return _generate_html(
        cosmos_db_id,
        "キャンセル処理完了",
        "既存の予定は削除されました。<br>以下のボタンから新たに日程をご入力ください。",
        [
            {
                "url": f"{config['CLIENT_URL']}/appointment?cosmos_db_id={cosmos_db_id}",
                "text": "日程再調整画面へ",
                "class": "bg-blue-500 hover:bg-blue-700"
            }
        ]
    )

def _generate_html(title: str, message: str, buttons: list) -> HTMLResponse:
    """HTMLレスポンスを生成"""
    buttons_html = "".join([
        f'<a href="{button["url"]}" '
        f'class="inline-block {button["class"]} text-white font-bold py-3 px-6 rounded text-xl">'
        f'{button["text"]}</a>'
        for button in buttons
    ])
    
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 flex items-center justify-center min-h-screen">
        <div class="bg-white shadow-xl rounded-lg p-12 max-w-xl text-center">
            <h1 class="text-3xl font-bold mb-6">{title}</h1>
            <p class="mb-8 text-lg">{message}</p>
            <div class="flex justify-center space-x-6">
                {buttons_html}
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)
