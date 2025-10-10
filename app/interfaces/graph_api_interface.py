from typing import Protocol, Any
from app.schemas.form import ScheduleRequest


class GraphAPIClientInterface(Protocol):
    def refresh_token(self) -> None:
        ...

    def post_request(
        self, url: str, body: dict[str, Any], timeout: int = 60
    ) -> dict[str, Any] | None:
        ...

    def get_schedules(self, schedule_req: ScheduleRequest) -> list[dict[str, Any]]:
        ...

    def register_event(
        self, employee_email: str, event: dict[str, Any]
    ) -> dict[str, Any]:
        ...

    def send_email(
        self, sender_email: str, target_employee_email: str, subject: str, body: str
    ) -> None:
        ...

    def update_event_time(
        self, employee_email: str, event_id: str, start_datetime: str, end_datetime: str
    ) -> None:
        ...

    def delete_event(self, employee_email: str, event_id: str) -> None:
        ...
