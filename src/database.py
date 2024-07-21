from sqlalchemy import create_engine, text
from pymongo import MongoClient

# MySQL connection string
db_connection_string = "mysql+pymysql://avnadmin:AVNS_TTYe0dDgdtJRZpF8DwC@db-proj-db-proj.h.aivencloud.com:12733/DBProject"

# Create engine with minimal SSL arguments
engine = create_engine(db_connection_string, connect_args={"ssl": {"ssl": True}})

# MongoDB connection string
mongodb_connection_string = "mongodb://mo9695_DBProject:Cisco123@mongo6.serv00.com:27017/mo9695_DBProject"

# Create a MongoDB client
mongo_client = MongoClient(mongodb_connection_string)

# Access the specific database
mongo_db = mongo_client["mo9695_DBProject"]

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

# Function to display users (for verification)
def display_users(engine):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM user"))
        for row in result:
            print(row)

# Example usage
# reset_auto_increment(engine)
# cleanup_user_related_tables(engine)
# display_users(engine)
