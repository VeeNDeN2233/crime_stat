import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

try:
    # Try to connect to the database
    conn = psycopg2.connect(**DB_CONFIG)
    print("Успешное подключение к базе данных!")
    
    # Create a cursor
    cur = conn.cursor()
    
    # Execute a test query
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"Версия PostgreSQL: {version[0]}")
    
    # Close the cursor and connection
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Ошибка подключения к базе данных: {str(e)}") 