from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models import get_user_by_username
from datetime import datetime

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
        if user.is_blocked:
            flash('Ваша учётная запись заблокирована', 'danger')
            return render_template('login.html')
        if user.blocked_until and user.blocked_until > datetime.now():
            flash(f'Учётная запись заблокирована до {user.blocked_until}', 'danger')
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