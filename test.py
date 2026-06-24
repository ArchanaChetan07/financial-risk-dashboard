import mysql.connector
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Database connection details
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

# Test connection
try:
    connection = mysql.connector.connect(**DB_CONFIG)
    print("Connection successful!")
except Exception as e:
    print(f"Error connecting to database: {e}")
finally:
    if connection.is_connected():
        connection.close()
