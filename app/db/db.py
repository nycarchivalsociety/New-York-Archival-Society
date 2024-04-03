import psycopg2
import os

# Remove the incorrect import of register_uuid

# Function to establish database connection
def get_db_connection():
    DATABASE_URL = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Function to execute SQL commands
def execute_sql(sql, conn_params):
    # Extract connection parameters and construct connection string
    conn_str = f"dbname='{conn_params['database']}' user='{conn_params['user']}' password='{conn_params['password']}' host='{conn_params['host']}' port='{conn_params['port']}' sslmode='{conn_params['sslmode']}'"
    conn = psycopg2.connect(conn_str)
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    conn.close()
