
from typing import Protocol, Any
from app.schemas.schedule import AppointmentRequest

class AppointmentRepositoryInterface(Protocol):
    def get_appointment_by_cosmos_db_id(self, cosmos_db_id: str) -> Any:
        ...

    def create_appointment(self, appointment_req: AppointmentRequest) -> None:
        ...

    def update_schedule_interview_datetime(self, cosmos_db_id: str, new_schedule_interview_datetime: str) -> None:
        ...

    def delete_appointment(self, cosmos_db_id: str) -> None:
        ...