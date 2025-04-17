import pymysql

pymysql.install_as_MySQLdb()

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

Users_Base = declarative_base()
