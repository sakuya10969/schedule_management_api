from typing import Protocol, Any

class EmployeeDirectoryRepositoryInterface(Protocol):
    def get_all_employee_directory(self) -> Any:
        ...