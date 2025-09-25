from sqlalchemy import create_engine, MetaData
from sqlalchemy.engine import URL

engine = create_engine(
    URL.create(
        "mssql+pyodbc",
        username="azureuser",
        password="SRM-password",
        host="srm-server-k.database.windows.net",
        port=1433,
        database="db-SRM-K",
        query={
            "driver": "ODBC Driver 18 for SQL Server",
            "Encrypt": "yes",
        },
    ),
    echo=True,
    fast_executemany=True,
    pool_pre_ping=True,
)

metadata = MetaData()
