import os
from psycopg2 import pool
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "crime_stat"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "8843"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

def get_connection_pool():
    try:
        return pool.SimpleConnectionPool(
            minconn=5,  # Увеличиваем минимальное количество соединений
            maxconn=20, # Увеличиваем максимальное количество соединений
            **DB_CONFIG
        )
    except Exception as e:
        logger.error(f"Ошибка создания пула соединений: {str(e)}")
        raise

connection_pool = get_connection_pool()

def get_db_connection():
    try:
        return connection_pool.getconn()
    except Exception as e:
        logger.error(f"Ошибка получения соединения из пула: {str(e)}")
        raise

def release_db_connection(conn):
    try:
        connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Ошибка возврата соединения в пул: {str(e)}")
        raise 