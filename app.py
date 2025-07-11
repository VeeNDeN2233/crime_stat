import os
import logging
from flask import Flask, render_template, jsonify, request, send_file
from flask_caching import Cache
from db import get_db_connection, release_db_connection
from dotenv import load_dotenv
from flask_login import LoginManager, login_required, current_user
from models import get_user_by_id
from auth import bp as auth_bp
from admin import bp as admin_bp
from oop import bp_oop
import io
import openpyxl

log_path = os.getenv('LOG_FILE_PATH', 'project.log')
file_handler = logging.FileHandler(log_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)

# Для вывода в консоль (опционально)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

# Явно перенаправляем werkzeug логгер в root
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)
# (handlers уже есть у root_logger)

# Load environment variables
load_dotenv()

# Создание экземпляра приложения
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-very-secret-key")

# Настройка кэширования
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
})

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

# Flask-Login setup
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)

#
app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(bp_oop)

# Главная страница (карта + список преступлений)
@app.route('/')
@login_required
def index():
    # Диагностика: выводим обработчики логгера
    for handler in logger.handlers:
        logger.info(f'Handler: {handler}')
    # Прямая запись в файл для проверки
    with open('project.log', 'a', encoding='utf-8') as f:
        f.write('DIRECT WRITE TEST: user: %s\n' % (current_user.username if current_user.is_authenticated else 'anonymous'))
    logger.info('Index page accessed by user: %s', current_user.username if current_user.is_authenticated else 'anonymous')
    return render_template('index.html')

# Страница добавления нового преступления
@app.route('/add-crime')
@login_required
def add_crime():
    return render_template('add_crime.html')

# Страница со списком всех преступлений
@app.route('/all-crimes')
@login_required
def all_crimes():
    return render_template('all_crimes.html')

# Заготовка для прогноза патрулей
@app.route('/patrol-forecast')
@login_required
def patrol_forecast():
    return render_template('patrol_forecast.html')

# Система ООП (Охрана общественного порядка)
@app.route('/oop')
@login_required
def oop():
    return render_template('oop_deployment.html')

@app.route('/oop/deployment')
@login_required
def oop_deployment_partial():
    # Здесь будет формироваться HTML для второй вкладки (AJAX)
    # Пока что базовая форма и таблица
    from flask import render_template_string
    html = '''
    <form id="deployment-form" class="deployment-form">
        <label>Дата: <input type="date" name="date" required></label>
        <label>Количество личного состава: <input type="number" name="personnel" min="1" required></label>
    </form>
    <div class="deployment-table-wrapper">
        <table id="deployment-table">
            <thead>
                <tr><th>Район</th><th>Область</th></tr>
            </thead>
            <tbody>
                <!-- Динамические строки -->
            </tbody>
        </table>
        <button id="add-row">Добавить запись</button>
        <button id="calculate">Рассчитать расстановку</button>
    </div>
    <div id="deployment-map" style="width: 500px; height: 500px; float: right;"></div>
    <div id="deployment-result"></div>
    <button id="export-xlsx">Экспорт в XLSX</button>
    '''
    return render_template_string(html)

@app.route('/statistics')
@login_required
def statistics():
    return render_template('statistics.html')

# Функциональная схема проекта
@app.route('/scheme')
@login_required
def project_scheme():
    return render_template('project_scheme.html')

@app.route('/get_incidents', methods=['GET'])
@cache.cached(timeout=300)  # Кэшируем на 5 минут
def get_incidents():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, kusp_number, article, incident_date, incident_time, name, address, victim_name
            FROM incidents inner join departments on incidents.department_id = departments.id;
        """)
        rows = cur.fetchall()

        incidents = [{
            "id": row[0],
            "kusp_number": row[1],
            "article": row[2],
            "incident_date": row[3].strftime('%Y-%m-%d'),
            "incident_time": row[4].strftime('%H:%M:%S'),
            "name": row[5],
            "address": row[6],
            "victim_name": row[7]
        } for row in rows]

        return jsonify(incidents)
    except Exception as e:
        logger.error(f"Error in get_incidents: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)

@app.route('/api/crimes')
@cache.cached(timeout=300, query_string=True)  # Кэшируем с учетом параметров запроса
def get_crimes():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Получаем параметры фильтрации
        department_id = request.args.get('department_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        article = request.args.get('article')
        search = request.args.get('search')

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
            query += " AND i.article = %s"
            params.append(article)
        
        if search:
            query += " AND ("
            query += "i.address ILIKE %s OR "
            query += "i.kusp_number ILIKE %s OR "
            query += "CAST(i.article AS TEXT) ILIKE %s OR "
            query += "d.name ILIKE %s OR "
            query += "o.full_name ILIKE %s"
            query += ")"
            search_pattern = f"%{search}%"
            params.extend([search_pattern]*5)

        # Добавляем сортировку
        query += " ORDER BY i.incident_date DESC, i.incident_time DESC"

        logger.info(f"Executing query: {query} with params: {params}")
        cur.execute(query, params)
        rows = cur.fetchall()

        crimes = [{
            "incident_date": row[0].strftime('%Y-%m-%d') if row[0] else None,
            "incident_time": row[1].strftime('%H:%M:%S') if row[1] else None,
            "article": row[2],
            "kusp_number": row[3],
            "address": row[4],
            "department_name": row[5],
            "officer_name": row[6],
            "officer_phone": row[7]
        } for row in rows]

        return jsonify(crimes)
    except Exception as e:
        logger.error(f"Error in get_crimes: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)

@app.route('/api/crimes', methods=['POST'])
def add_crime_api():
    conn = None
    cur = None
    try:
        data = request.get_json()
        
        # Проверка обязательных полей
        required_fields = ['kusp_number', 'article', 'incident_date', 'incident_time', 
                         'address', 'department_id', 'duty_officer_id']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Отсутствует обязательное поле: {field}"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        # Вставка данных
        cur.execute("""
            INSERT INTO incidents (
                kusp_number, article, incident_date, incident_time,
                address, department_id, duty_officer_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data['kusp_number'],
            data['article'],
            data['incident_date'],
            data['incident_time'],
            data['address'],
            data['department_id'],
            data['duty_officer_id']
        ))
        
        new_id = cur.fetchone()[0]
        conn.commit()
        
        return jsonify({"success": True, "id": new_id})
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error adding crime: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)

@app.route('/api/districts')
@login_required
def get_districts():
    """Вернуть список районов города. Используется вкладкой расстановки сил"""
    conn = cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM districts ORDER BY name")
        districts = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
        return jsonify(districts)
    except Exception as e:
        logger.error(f"Error getting districts: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)

@app.route('/api/departments')
def get_departments():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
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
            release_db_connection(conn)

@app.route('/api/officers')
def get_officers():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id, full_name FROM duty_officers ORDER BY full_name")
        officers = [{"id": row[0], "full_name": row[1]} for row in cur.fetchall()]
        
        return jsonify(officers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)

@app.route('/api/statistics')
def get_statistics():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Получаем параметры фильтрации
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        department_id = request.args.get('department_id')
        date_filter = ""
        params = []
        if start_date:
            date_filter += " AND incident_date >= %s"
            params.append(start_date)
        if end_date:
            date_filter += " AND incident_date <= %s"
            params.append(end_date)
        if department_id:
            date_filter += " AND department_id = %s"
            params.append(department_id)

        # Статистика по дням недели
        cur.execute(f"""
            SELECT 
                EXTRACT(DOW FROM incident_date) as day_of_week,
                COUNT(*) as count
            FROM incidents
            WHERE 1=1 {date_filter}
            GROUP BY day_of_week
            ORDER BY day_of_week;
        """, params)
        days_stats = cur.fetchall()
        days_data = {
            'labels': ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'],
            'data': [0] * 7
        }
        for day, count in days_stats:
            days_data['data'][int(day)] = count

        # Статистика по статьям
        cur.execute(f"""
            SELECT 
                article,
                COUNT(*) as count
            FROM incidents
            WHERE 1=1 {date_filter}
            GROUP BY article
            ORDER BY count DESC
            LIMIT 10;
        """, params)
        articles_stats = cur.fetchall()
        articles_data = {
            'labels': [f"ст. {article}" for article, _ in articles_stats],
            'data': [count for _, count in articles_stats]
        }

        # Статистика по отделам (для диаграммы)
        cur.execute(f"""
            SELECT 
                d.name,
                COUNT(*) as count
            FROM incidents i
            JOIN departments d ON i.department_id = d.id
            WHERE 1=1 {date_filter}
            GROUP BY d.name
            ORDER BY count DESC;
        """, params)
        departments_stats = cur.fetchall()
        departments_data = {
            'labels': [name for name, _ in departments_stats],
            'data': [count for _, count in departments_stats]
        }

        # Статистика по районам города
        cur.execute(f"""
            SELECT 
                d.name as district,
                COUNT(i.id) as count
            FROM districts d
            LEFT JOIN incidents i ON i.district_id = d.id
            WHERE 1=1 {date_filter if date_filter else ''}
            GROUP BY d.name
            ORDER BY count DESC;
        """, params)
        districts_stats = cur.fetchall()
        districts_data = {
            'labels': [],
            'data': []
        }
        for district, count in districts_stats:
            if district:
                districts_data['labels'].append(district)
                districts_data['data'].append(count)

        return jsonify({
            'days': days_data,
            'articles': articles_data,
            'departments': departments_data,
            'districts': districts_data
        })

    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)

@app.route('/api/patrol-calc', methods=['POST'])
@login_required
def patrol_calc():
    """Рассчитать количество пеших и мобильных патрулей пропорционально числу преступлений в районах."""
    data = request.get_json()
    personnel = int(data.get('personnel', 0))
    rows = data.get('rows', [])  # [{'districtId','districtName','area'}]
    if not rows or personnel <= 0:
        return jsonify({"error": "Неверные данные"}), 400

    district_ids = [int(r['districtId']) for r in rows]

    conn = cur = None
    crime_counts = []  # количество преступлений в каждой строке rows
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Считаем преступления только по району – без геометрии, чтобы избежать ошибок PostGIS
        crimes_by_district = {did: 1 for did in district_ids}
        try:
            cur.execute(
                """
                SELECT district_id, COUNT(*)
                FROM incidents
                WHERE district_id = ANY(%s) AND incident_date >= NOW() - INTERVAL '30 days'
                GROUP BY district_id
                """,
                (district_ids,)
            )
            for did, cnt in cur.fetchall():
                crimes_by_district[int(did)] = cnt or 1
        except Exception as e:
            logger.error(f"Error counting crimes by district: {e}")
        # формируем список в том же порядке, что rows
        for r in rows:
            crime_counts.append(crimes_by_district.get(int(r['districtId']), 1))
    except Exception as e:
        logger.error(f"patrol_calc crime count error: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            release_db_connection(conn)

    total_crimes = sum(crime_counts) or 1
    total_patrols_available = max(1, personnel // 2)

    result = []
    for idx, r in enumerate(rows):
        crime_ratio = crime_counts[idx] / total_crimes
        patrols_for_row = max(1, round(total_patrols_available * crime_ratio))
        foot = patrols_for_row // 2 + patrols_for_row % 2
        mobile = patrols_for_row // 2
        result.append({
            "districtId": int(r['districtId']),
            "districtName": r['districtName'],
            "footPatrols": foot,
            "mobilePatrols": mobile,
            "area": r.get('area'),
            "crimes": crime_counts[idx]
        })
    return jsonify(result)


@app.route('/oop/export_xlsx', methods=['POST'])
@login_required
def export_deployment_xlsx():
    data = request.get_json()
    rows = data.get('rows', [])
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='deployment.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Запуск сервера
if __name__ == '__main__':
    # Убедитесь, что порт 5000 свободен. Если нет, измените его на другой (например, 8080).
    app.run(debug=True, port=5000)