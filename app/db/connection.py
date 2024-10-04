from app.db.db import db  # Ensure this import is correct
import psycopg2
import os

def init_db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    db.init_app(app)

def get_db_connection():
    DATABASE_URL = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def execute_sql(sql, conn_params):
    conn_str = f"dbname='{conn_params['database']}' user='{conn_params['user']}' password='{conn_params['password']}' host='{conn_params['host']}' port='{conn_params['port']}' sslmode='{conn_params['sslmode']}'"
    conn = psycopg2.connect(conn_str)
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    conn.close()