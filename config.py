import os

class Config:
    SECRET_KEY = "clave_secreta"
    
    # Configuration for MySQL connection
    MYSQL_USER = "root"
    MYSQL_PASSWORD = "1234"
    MYSQL_HOST = "localhost"  # IP of MySQL server
    MYSQL_DB = "oncotrack_db"

    # URI for SQLAlchemy (use pymysql as driver)
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

