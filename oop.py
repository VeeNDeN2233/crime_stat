from flask import Blueprint, jsonify
from db import get_db_connection, release_db_connection

bp_oop = Blueprint('oop', __name__)

@bp_oop.route('/api/districts')
def get_districts():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM districts ORDER BY name")
    districts = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]
    cur.close()
    release_db_connection(conn)
    return jsonify(districts)

# Здесь будут другие API-методы для ООП
