import os
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "crime_stat"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "8843"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

connection_pool = pool.SimpleConnectionPool(
    1,  # minconn
    10, # maxconn
    **DB_CONFIG
) 