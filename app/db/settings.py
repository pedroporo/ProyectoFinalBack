from dotenv import load_dotenv
import os
from sshtunnel import SSHTunnelForwarder

load_dotenv()

# import pymysql
#
# pymysql.install_as_MySQLdb()
from app.db.models import Database
from app.db import Users_Base
import asyncio

DATABASE_NAME = os.getenv('MYSQL_DATABASE')
DB_USER = os.getenv('MYSQL_USER')
DB_PASS = os.getenv('MYSQL_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

local_db = Database(DATABASE_NAME=DATABASE_NAME, DB_USER=DB_USER, DB_PASS=DB_PASS, DB_HOST=DB_HOST, DB_PORT=DB_PORT,
                    BASE=Users_Base)

