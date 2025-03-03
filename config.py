import os

class Config:
    SECRET_KEY = "abcd"
    MYSQL_USER = "root"
    MYSQL_PASSWORD = "Ivon1234%40"
    MYSQL_HOST = "localhost"
    MYSQL_DB = "oncotrack_db"

    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:Ivon1234%40@localhost/oncotrack_db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
