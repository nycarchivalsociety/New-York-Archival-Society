from app import create_app
from app.db.db import execute_sql
from app.db.models import create_tables_sql

# Set up your connection parameters
connection_parameters = {
    "host": "dpg-co2a6e8l6cac739j2mh0-a.ohio-postgres.render.com",
    "port": "5432",
    "database": "nyas_db",
    "user": "nyas_db_user",
    "password": "QQ9HfLAqRJq6mZRTx6gZF5uZ4jgvXba3",
    "sslmode": "require"  # Render's databases require SSL.
}

if __name__ == '__main__':
    # Call the factory function to get the Flask app instance
    app = create_app()
    execute_sql(create_tables_sql, connection_parameters)
    print("Database and tables created successfully.")
    app.run()
