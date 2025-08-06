from sqlalchemy import create_engine, MetaData, select
from sqlalchemy.engine import URL
from app.config.config import get_config

config = get_config()


class EmployeeDirectoryRepository:
    def __init__(self):
        self.engine = create_engine(
            URL.create(
                "mssql+pyodbc",
                username="azureuser",
                password="SRM-password",
                host="srm-server-k.database.windows.net",
                port=1433,
                database="db-SRM-K",
                query={"driver": "ODBC Driver 18 for SQL Server"},
            ),
            echo=True,
            fast_executemany=True,
        )

        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)
        self.employee_directory = self.meta.tables["employee_directory"]

    def get_all_employee_directory(self):
        with self.engine.begin() as conn:
            stmt = select(self.employee_directory)
            result = conn.execute(stmt)
            return result.fetchall()
