from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import get_user_by_id, get_user_by_username
from werkzeug.security import generate_password_hash
import psycopg2
from db import connection_pool
from functools import wraps
from datetime import datetime, timedelta

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
    cur.execute("SELECT id, username, is_admin, is_blocked, blocked_until, created_at FROM users ORDER BY id")
    users = cur.fetchall()
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