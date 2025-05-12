from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models import get_user_by_username
from datetime import datetime
from db import connection_pool

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)
        if not user:
            flash('Пользователь не найден', 'danger')
            return render_template('login.html')

        # Автоматический сброс блокировки, если срок истёк
        if user.blocked_until and user.blocked_until <= datetime.now():
            conn = connection_pool.getconn()
            cur = conn.cursor()
            cur.execute("UPDATE users SET is_blocked = FALSE, blocked_until = NULL WHERE id = %s", (user.id,))
            conn.commit()
            cur.close()
            connection_pool.putconn(conn)
            user.is_blocked = False
            user.blocked_until = None

        if user.is_actually_blocked:
            if user.blocked_until:
                flash(f'Учётная запись заблокирована до {user.blocked_until}', 'danger')
            else:
                flash('Ваша учётная запись заблокирована', 'danger')
            return render_template('login.html')
        if not user.check_password(password):
            flash('Неверный пароль', 'danger')
            return render_template('login.html')

        print(f"USER: {user}")
        print(f"USER ID: {user.id}")
        print(f"USER get_id(): {user.get_id()} (type: {type(user.get_id())})")
        print(f"USER is_authenticated: {user.is_authenticated}")

        login_user(user)
        return redirect(url_for('index'))
    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login')) 