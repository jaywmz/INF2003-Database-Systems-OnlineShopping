from sqlalchemy import create_engine, text

# Connection string without ssl-mode
db_connection_string = "mysql+pymysql://avnadmin:AVNS_TTYe0dDgdtJRZpF8DwC@db-proj-db-proj.h.aivencloud.com:12733/DBProject"

# Create engine with minimal SSL arguments
engine = create_engine(db_connection_string,
    connect_args={
        "ssl": {
            "ssl": True
        }
    }
)

# Using the connection to execute a query
with engine.connect() as conn:
    result = conn.execute(text("select * from user"))
    for row in result:
        print(row)
