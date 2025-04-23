from fastapi import HTTPException, status
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from contextlib import asynccontextmanager
from sqlalchemy import text
from sshtunnel import SSHTunnelForwarder
import asyncio
from sqlalchemy_utils import database_exists, create_database

load_dotenv()


#
# ssh_tunnel = SSHTunnelForwarder(
#     os.getenv('SERVER_IP'),
#     ssh_username=os.getenv('SSH_USERNAME'),
#     ssh_password=os.getenv('SSH_PASSWORD'),
#     remote_bind_address=('localhost', 3306)
# )
# ssh_tunnel.start()


# DATABASE_NAME = os.getenv('MYSQL_DATABASE')
# DB_USER = os.getenv('MYSQL_USER')
# DB_PASS = os.getenv('MYSQL_PASSWORD')
# DB_HOST = os.getenv('DB_HOST')
# DB_PORT = os.getenv('DB_PORT')


# DATABASE_URL = f"mysql+asyncmy://{DB_USER}:{DB_PASS}@localhost:{ssh_tunnel.local_bind_port}/{DATABASE_NAME}"

class Database:
    def __init__(self, DB_USER, DB_PASS, DB_HOST, DB_PORT, DATABASE_NAME, BASE):
        self.DB_USER = DB_USER
        self.DB_PASS = DB_PASS
        self.DB_HOST = DB_HOST
        self.DB_PORT = DB_PORT
        self.DATABASE_NAME = DATABASE_NAME
        self.DATABASE_URL = f"mysql+asyncmy://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DATABASE_NAME}"
        self.engine = create_async_engine(self.DATABASE_URL, echo=False)
        self.async_session_factory = async_sessionmaker(bind=self.engine, expire_on_commit=False)
        self.BASE = BASE

    async def init_models(self):
        async with self.engine.begin() as conn:
            # await conn.run_sync(self.BASE.metadata.drop_all)
            await conn.run_sync(self.BASE.metadata.create_all)

    async def get_db_session(self) -> AsyncSession:
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def get_db_session_class(self) -> AsyncSession:
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def ensure_database_exists(self):
        # Conexión sin especificar base de datos
        url = f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/information_schema"
        engine = create_async_engine(url, echo=False)
        # if not database_exists(self.engine.url):
        #     create_database(self.engine.url)
        async with engine.connect() as conn:
            result = await conn.execute(
                text(f'SELECT SCHEMA_NAME FROM SCHEMATA WHERE SCHEMA_NAME = "{self.DATABASE_NAME}"'))
            exists = result.first()
            if not exists:
                await conn.execute(
                    text(f"CREATE DATABASE {self.DATABASE_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        await engine.dispose()
        # print(database_exists(self.engine.url))

    async def init(self):
        await self.ensure_database_exists()
        # self.engine = create_async_engine(self.DATABASE_URL, echo=False)
        # self.async_session_factory = async_sessionmaker(bind=self.engine, expire_on_commit=False)
