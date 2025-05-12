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
#asyncio.run(local_db.init())
# print("¡Tablas creadas exitosamente!")
# ssh_tunnel= SSHTunnelForwarder(
#     os.getenv('SERVER_IP'),
#     ssh_username=os.getenv('SSH_USERNAME'),
#     ssh_password=os.getenv('SSH_PASSWORD'),
#     remote_bind_address=('localhost',3306)
# )
# ssh_tunnel.start()
#
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': os.getenv('MYSQL_DATABASE'),
#         'USER': os.getenv('MYSQL_USER'),
#         'PASSWORD': os.getenv('MYSQL_PASSWORD'),
#         'HOST': os.getenv('DB_HOST'),
#         'PORT': os.getenv('DB_PORT'),
#     },
#     'sshtunnel_db':{
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': os.getenv('MYSQL_DATABASE'),
#         'USER': os.getenv('MYSQL_USER'),
#         'PASSWORD': os.getenv('MYSQL_PASSWORD'),
#         'HOST': 'localhost',
#         'PORT': ssh_tunnel.local_bind_port,
#     },
# }
