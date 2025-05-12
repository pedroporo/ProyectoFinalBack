import json
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy import text, NullPool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# from sqlalchemy.pool import NullPool

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
        #self.engine = create_async_engine(self.DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=3600,poolclass=NullPool, pool_reset_on_return=None, isolation_level="AUTOCOMMIT")
        self.engine = create_async_engine(self.DATABASE_URL, echo=False, pool_pre_ping=True,poolclass=NullPool)
        #self.engine = None
        # self.engine = create_async_engine(self.DATABASE_URL, echo=True)
        self.async_session_factory = async_sessionmaker(bind=self.engine, expire_on_commit=False)
        #self.async_session_factory = None
        self.BASE = BASE

    def to_dict(self):
        """Convierte la instancia del modelo a un diccionario serializable"""
        return {
            'DB_USER': self.DB_USER,
            'DB_PASS': self.DB_PASS,
            'DB_HOST': self.DB_HOST,
            'DB_PORT': self.DB_PORT,
            'DATABASE_NAME': self.DATABASE_NAME,
            'DATABASE_URL': self.DATABASE_URL,
        }

    def toJSON(self):

        return json.dumps(self.to_dict(), indent=4, sort_keys=True, default=str)

    async def init_models(self):
        async with self.engine.begin() as conn:
            #if self.DATABASE_NAME != 'fastapi_app' :
            #    await conn.run_sync(self.BASE.metadata.drop_all)

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
            await conn.close()
        await engine.dispose()
        # print(database_exists(self.engine.url))

    async def init(self):
        await self.ensure_database_exists()
        #self.engine = create_async_engine(self.DATABASE_URL, echo=False, pool_pre_ping=True,poolclass=NullPool)
        #self.async_session_factory = async_sessionmaker(bind=self.engine, expire_on_commit=False)
