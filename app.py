from flask import Flask, render_template, jsonify, request
import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Создание экземпляра приложения
app = Flask(__name__)

# Database connection pool
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "crime_stat"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "8843"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

# Create connection pool
try:
    connection_pool = pool.SimpleConnectionPool(
        1,  # minconn
        10, # maxconn
        **DB_CONFIG
    )
except Exception as e:
    logger.error(f"Failed to create connection pool: {str(e)}")
    raise

def check_table_exists(cursor, table_name):
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        );
    """, (table_name,))
    return cursor.fetchone()[0]

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# Главная страница (карта + список преступлений)
@app.route('/')
def index():
    return render_template('index.html')

# Страница добавления нового преступления
@app.route('/add-crime')
def add_crime():
    return render_template('add_crime.html')

# Страница со списком всех преступлений
@app.route('/all-crimes')
def all_crimes():
    return render_template('all_crimes.html')

# Заготовка для прогноза патрулей
@app.route('/patrol-forecast')
def patrol_forecast():
    return render_template('patrol_forecast.html')

@app.route('/statistics')
def statistics():
    return render_template('statistics.html')

@app.route('/get_incidents', methods=['GET'])
def get_incidents():
    try:
        # Подключение к базе данных
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Выборка данных из таблицы incidents
        cur.execute("""
            SELECT id, kusp_number, article, incident_date, incident_time, name, address, victim_name
            FROM incidents inner join departments on incidents.department_id = departments.id;
        """)
        rows = cur.fetchall()

        # Преобразование данных в JSON
        incidents = []
        for row in rows:
            incidents.append({
                "id": row[0],
                "kusp_number": row[1],
                "article": row[2],
                "incident_date": row[3].strftime('%Y-%m-%d'),
                "incident_time": row[4].strftime('%H:%M:%S'),
                "name": row[5],
                "address": row[6],
                "victim_name": row[7]
            })

        # Закрытие соединения
        cur.close()
        conn.close()

        return jsonify(incidents)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/crimes')
def get_crimes():
    conn = None
    cur = None
    try:
        conn = connection_pool.getconn()
        cur = conn.cursor()

        # Получаем параметры фильтрации
        department_id = request.args.get('department_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        article = request.args.get('article')

        # Проверка существования таблицы
        if not check_table_exists(cur, 'incidents'):
            logger.error("Table 'incidents' does not exist")
            return jsonify({"error": "Table 'incidents' does not exist"}), 500

        # Базовый запрос
        query = """
            SELECT 
                i.incident_date,
                i.incident_time,
                i.article,
                i.kusp_number,
                i.address,
                d.name as department_name,
                o.full_name as officer_name,
                o.phone as officer_phone
            FROM incidents i
            LEFT JOIN departments d ON i.department_id = d.id
            LEFT JOIN duty_officers o ON i.duty_officer_id = o.id
            WHERE 1=1
        """
        params = []

        # Добавляем условия фильтрации
        if department_id:
            query += " AND i.department_id = %s"
            params.append(department_id)
        
        if start_date:
            query += " AND i.incident_date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND i.incident_date <= %s"
            params.append(end_date)
        
        if article:
            query += " AND i.article ILIKE %s"
            params.append(f'%{article}%')

        # Добавляем сортировку
        query += " ORDER BY i.incident_date DESC, i.incident_time DESC"

        logger.info(f"Executing query: {query} with params: {params}")
        cur.execute(query, params)
        rows = cur.fetchall()
        logger.info(f"Query executed successfully, fetched {len(rows)} rows")

        # Преобразование данных в JSON
        crimes = []
        for row in rows:
            crimes.append({
                "incident_date": row[0].strftime('%Y-%m-%d') if row[0] else None,
                "incident_time": row[1].strftime('%H:%M:%S') if row[1] else None,
                "article": row[2],
                "kusp_number": row[3],
                "address": row[4],
                "department_name": row[5],
                "officer_name": row[6],
                "officer_phone": row[7]
            })

        logger.info(f"Successfully retrieved {len(crimes)} crimes")
        return jsonify(crimes)
    except psycopg2.OperationalError as e:
        error_msg = f"Database connection error: {str(e)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500
    except psycopg2.Error as e:
        error_msg = f"Database error: {str(e)}\nQuery: {query if 'query' in locals() else 'Not available'}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            connection_pool.putconn(conn)

@app.route('/api/departments')
def get_departments():
    conn = None
    cur = None
    try:
        conn = connection_pool.getconn()
        cur = conn.cursor()

        cur.execute("SELECT id, name FROM departments ORDER BY name")
        departments = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
        
        return jsonify(departments)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            connection_pool.putconn(conn)

# Запуск сервера
if __name__ == '__main__':
    # Убедитесь, что порт 5000 свободен. Если нет, измените его на другой (например, 8080).
    app.run(debug=True, port=5000)