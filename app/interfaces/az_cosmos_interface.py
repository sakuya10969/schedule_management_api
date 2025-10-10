from typing import Protocol, Any


class AzCosmosDBClientInterface(Protocol):
    def create_form_data(self, payload: dict[str, Any]) -> str:
        ...

    def get_form_data(self, cosmos_db_id: str) -> dict[str, Any]:
        ...

    def update_form_data(
        self,
        cosmos_db_id: str,
        schedule_interview_datetime: str,
        event_ids: dict[str, str],
    ) -> None:
        ...

    def remove_candidate_from_other_forms(
        self,
        selected_cosmos_db_id: str,
        selected_schedule_interview_datetime: list[str],
    ) -> None:
        ...

    def confirm_form(self, cosmos_db_id: str) -> None:
        ...

    def finalize_form(
        self, cosmos_db_id: str, selected_schedule_interview_datetime: list[str]
    ) -> None:
        ...

    def delete_form_data(self, cosmos_db_id: str) -> None:
        ...
