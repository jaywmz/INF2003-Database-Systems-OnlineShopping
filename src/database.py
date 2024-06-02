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

# Function to reset auto-increment values
def reset_auto_increment(engine):
    with engine.connect() as conn:
        # Disable foreign key checks
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

        # Reset auto-increment values
        conn.execute(text("ALTER TABLE user AUTO_INCREMENT = 1;"))
        conn.execute(text("ALTER TABLE seller AUTO_INCREMENT = 1;"))
        conn.execute(text("ALTER TABLE customer AUTO_INCREMENT = 1;"))
        conn.execute(text("ALTER TABLE geolocation AUTO_INCREMENT = 1;"))

        # Enable foreign key checks
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

        conn.commit()
        print("Auto-increment values reset successfully.")

# Execute the function
# reset_auto_increment(engine)

# Function to clean up user-related tables
def cleanup_user_related_tables(engine):
    with engine.connect() as conn:
        # Disable foreign key checks
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))

        # Delete records from user, seller, customer, and geolocation tables
        conn.execute(text("DELETE FROM user;"))
        conn.execute(text("DELETE FROM seller;"))
        conn.execute(text("DELETE FROM customer;"))
        conn.execute(text("DELETE FROM geolocation;"))

        # Enable foreign key checks
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))

        conn.commit()
        print("Cleaned up user-related tables successfully.")

# Execute cleanup
# cleanup_user_related_tables(engine)

# Function to display users (for verification)
def display_users(engine):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM user"))
        for row in result:
            print(row)

# Display users after cleanup
display_users(engine)

