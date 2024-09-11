from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

# Connection string
engine = create_engine('postgresql+psycopg2://postgres:jeziel3ds48@localhost:5432/nyc_archival_society')

try:
    # Establish the connection
    with engine.connect() as connection:
        print("Connection to the PostgreSQL database established successfully.")
except SQLAlchemyError as e:
    # If an error occurs, this error message will be printed
    print(f"An error occurred while connecting to the database: {e}")
