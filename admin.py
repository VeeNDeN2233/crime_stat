from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import get_user_by_id, get_user_by_username, User
from werkzeug.security import generate_password_hash
import psycopg2
from db import connection_pool
from functools import wraps
from datetime import datetime, timedelta
import os

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Доступ только для администратора', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/users')
@login_required
@admin_required
def users():
    conn = connection_pool.getconn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, is_admin, is_blocked, blocked_until, created_at FROM users ORDER BY id")
    rows = cur.fetchall()
    users = []
    for row in rows:
        # row: id, username, password_hash, is_admin, is_blocked, blocked_until, created_at
        user = User(row[0], row[1], row[2], row[3], row[4], row[5])
        user.created_at = row[6]
        users.append(user)
    cur.close()
    connection_pool.putconn(conn)
    return render_template('users_admin.html', users=users)

@bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    username = request.form['username']
    password = request.form['password']
    is_admin = bool(request.form.get('is_admin'))
    password_hash = generate_password_hash(password)
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, %s)", (username, password_hash, is_admin))
        conn.commit()
        flash('Пользователь создан', 'success')
    except psycopg2.Error as e:
        flash('Ошибка: ' + str(e), 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.users'))

@bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('Нельзя удалить самого себя', 'danger')
        return redirect(url_for('admin.users'))
    conn = connection_pool.getconn()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    connection_pool.putconn(conn)
    flash('Пользователь удалён', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/users/block/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def block_user(user_id):
    minutes = int(request.form.get('minutes', 0))
    blocked_until = datetime.now() + timedelta(minutes=minutes) if minutes > 0 else None
    conn = connection_pool.getconn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_blocked = TRUE, blocked_until = %s WHERE id = %s", (blocked_until, user_id))
    conn.commit()
    cur.close()
    connection_pool.putconn(conn)
    flash('Пользователь заблокирован', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/users/unblock/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def unblock_user(user_id):
    conn = connection_pool.getconn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_blocked = FALSE, blocked_until = NULL WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    connection_pool.putconn(conn)
    flash('Пользователь разблокирован', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/users/change_password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def change_password(user_id):
    new_password = request.form.get('new_password')
    if not new_password:
        flash('Пароль не может быть пустым', 'danger')
        return redirect(url_for('admin.users'))
    
    password_hash = generate_password_hash(new_password)
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
        conn.commit()
        flash('Пароль изменён', 'success')
    except psycopg2.Error as e:
        flash('Ошибка: ' + str(e), 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.users'))

@bp.route('/users/toggle_admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    if user_id == current_user.id:
        flash('Нельзя изменить свои права администратора', 'danger')
        return redirect(url_for('admin.users'))
    
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET is_admin = NOT is_admin WHERE id = %s", (user_id,))
        conn.commit()
        flash('Права администратора изменены', 'success')
    except psycopg2.Error as e:
        flash('Ошибка: ' + str(e), 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.users'))

@bp.route('/logs')
@login_required
@admin_required
def logs():
    log_path = os.getenv('LOG_FILE_PATH', 'project.log')
    try:
        with open(log_path, encoding='utf-8') as f:
            log_content = f.read()
    except Exception as e:
        log_content = f'Ошибка при чтении лога: {e}'
    return render_template('admin_logs.html', log_content=log_content)

@bp.route('/logs/clear', methods=['POST'])
@login_required
@admin_required
def clear_logs():
    import os
    log_path = os.getenv('LOG_FILE_PATH', 'project.log')
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('')
        flash('Журнал логов очищён', 'success')
    except Exception as e:
        flash(f'Ошибка при очистке лога: {e}', 'danger')
    return redirect(url_for('admin.logs'))

@bp.route('/directories')
@login_required
@admin_required
def directories():
    conn = connection_pool.getconn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, address, phone FROM departments ORDER BY id")
    departments = cur.fetchall()
    cur.execute("SELECT id, name, description FROM districts ORDER BY id")
    districts = cur.fetchall()
    cur.execute("SELECT id, full_name, rank, position, phone, department_id FROM duty_officers ORDER BY id")
    duty_officers = cur.fetchall()
    cur.execute("SELECT id, full_name, rank, position, phone, department_id FROM officers ORDER BY id")
    officers = cur.fetchall()
    # Для выпадающих списков отделов
    cur.execute("SELECT id, name FROM departments ORDER BY name")
    departments_list = cur.fetchall()
    cur.close()
    connection_pool.putconn(conn)
    return render_template('admin_directories.html', departments=departments, districts=districts, duty_officers=duty_officers, officers=officers, departments_list=departments_list)

@bp.route('/directories/departments/add', methods=['POST'])
@login_required
@admin_required
def add_department():
    name = request.form.get('name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    if not name:
        flash('Название не может быть пустым', 'danger')
        return redirect(url_for('admin.directories'))
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO departments (name, address, phone) VALUES (%s, %s, %s)", (name, address, phone))
        conn.commit()
        flash('Отдел добавлен', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.directories'))

@bp.route('/directories/departments/edit/<int:dep_id>', methods=['POST'])
@login_required
@admin_required
def edit_department(dep_id):
    name = request.form.get('name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    if not name:
        flash('Название не может быть пустым', 'danger')
        return redirect(url_for('admin.directories'))
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE departments SET name=%s, address=%s, phone=%s WHERE id=%s", (name, address, phone, dep_id))
        conn.commit()
        flash('Отдел обновлён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.directories'))

@bp.route('/directories/departments/delete/<int:dep_id>', methods=['POST'])
@login_required
@admin_required
def delete_department(dep_id):
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM departments WHERE id=%s", (dep_id,))
        conn.commit()
        flash('Отдел удалён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.directories'))

# DISTRICTS
@bp.route('/directories/districts/add', methods=['POST'])
@login_required
@admin_required
def add_district():
    name = request.form.get('name')
    description = request.form.get('description')
    if not name:
        flash('Название не может быть пустым', 'danger')
        return redirect(url_for('admin.directories'))
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO districts (name, description) VALUES (%s, %s)", (name, description))
        conn.commit()
        flash('Район добавлен', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.directories'))

@bp.route('/directories/districts/edit/<int:dist_id>', methods=['POST'])
@login_required
@admin_required
def edit_district(dist_id):
    name = request.form.get('name')
    description = request.form.get('description')
    if not name:
        flash('Название не может быть пустым', 'danger')
        return redirect(url_for('admin.directories'))
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE districts SET name=%s, description=%s WHERE id=%s", (name, description, dist_id))
        conn.commit()
        flash('Район обновлён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.directories'))

@bp.route('/directories/districts/delete/<int:dist_id>', methods=['POST'])
@login_required
@admin_required
def delete_district(dist_id):
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM districts WHERE id=%s", (dist_id,))
        conn.commit()
        flash('Район удалён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.directories'))

# DUTY_OFFICERS
@bp.route('/directories/duty_officers/add', methods=['POST'])
@login_required
@admin_required
def add_duty_officer():
    full_name = request.form.get('full_name')
    rank = request.form.get('rank')
    position = request.form.get('position')
    phone = request.form.get('phone')
    department_id = request.form.get('department_id') or None
    if not full_name:
        flash('ФИО не может быть пустым', 'danger')
        return redirect(url_for('admin.directories'))
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO duty_officers (full_name, rank, position, phone, department_id) VALUES (%s, %s, %s, %s, %s)", (full_name, rank, position, phone, department_id if department_id else None))
        conn.commit()
        flash('Дежурный офицер добавлен', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.directories'))

@bp.route('/directories/duty_officers/edit/<int:off_id>', methods=['POST'])
@login_required
@admin_required
def edit_duty_officer(off_id):
    full_name = request.form.get('full_name')
    rank = request.form.get('rank')
    position = request.form.get('position')
    phone = request.form.get('phone')
    department_id = request.form.get('department_id') or None
    if not full_name:
        flash('ФИО не может быть пустым', 'danger')
        return redirect(url_for('admin.directories'))
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE duty_officers SET full_name=%s, rank=%s, position=%s, phone=%s, department_id=%s WHERE id=%s", (full_name, rank, position, phone, department_id if department_id else None, off_id))
        conn.commit()
        flash('Дежурный офицер обновлён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.directories'))

@bp.route('/directories/duty_officers/delete/<int:off_id>', methods=['POST'])
@login_required
@admin_required
def delete_duty_officer(off_id):
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM duty_officers WHERE id=%s", (off_id,))
        conn.commit()
        flash('Дежурный офицер удалён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.directories'))

# OFFICERS
@bp.route('/directories/officers/add', methods=['POST'])
@login_required
@admin_required
def add_officer():
    full_name = request.form.get('full_name')
    rank = request.form.get('rank')
    position = request.form.get('position')
    phone = request.form.get('phone')
    department_id = request.form.get('department_id') or None
    if not full_name:
        flash('ФИО не может быть пустым', 'danger')
        return redirect(url_for('admin.directories'))
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO officers (full_name, rank, position, phone, department_id) VALUES (%s, %s, %s, %s, %s)", (full_name, rank, position, phone, department_id if department_id else None))
        conn.commit()
        flash('Офицер добавлен', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.directories'))

@bp.route('/directories/officers/edit/<int:off_id>', methods=['POST'])
@login_required
@admin_required
def edit_officer(off_id):
    full_name = request.form.get('full_name')
    rank = request.form.get('rank')
    position = request.form.get('position')
    phone = request.form.get('phone')
    department_id = request.form.get('department_id') or None
    if not full_name:
        flash('ФИО не может быть пустым', 'danger')
        return redirect(url_for('admin.directories'))
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE officers SET full_name=%s, rank=%s, position=%s, phone=%s, department_id=%s WHERE id=%s", (full_name, rank, position, phone, department_id if department_id else None, off_id))
        conn.commit()
        flash('Офицер обновлён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.directories'))

@bp.route('/directories/officers/delete/<int:off_id>', methods=['POST'])
@login_required
@admin_required
def delete_officer(off_id):
    conn = connection_pool.getconn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM officers WHERE id=%s", (off_id,))
        conn.commit()
        flash('Офицер удалён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'danger')
    finally:
        cur.close()
        connection_pool.putconn(conn)
    return redirect(url_for('admin.directories')) 