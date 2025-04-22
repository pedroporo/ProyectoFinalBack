from fastapi import HTTPException, status
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from contextlib import asynccontextmanager
from sshtunnel import SSHTunnelForwarder
import asyncio
from app.db import Base
from app.db import Users_Base

load_dotenv()

ssh_tunnel = SSHTunnelForwarder(
    os.getenv('SERVER_IP'),
    ssh_username=os.getenv('SSH_USERNAME'),
    ssh_password=os.getenv('SSH_PASSWORD'),
    remote_bind_address=('localhost', 3306)
)
ssh_tunnel.start()

DATABASE_NAME = os.getenv('MYSQL_DATABASE')
DB_USER = os.getenv('MYSQL_USER')
DB_PASS = os.getenv('MYSQL_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

# DATABASE_URL = f"mysql+asyncmy://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DATABASE_NAME}"
DATABASE_URL = f"mysql+asyncmy://{DB_USER}:{DB_PASS}@localhost:{ssh_tunnel.local_bind_port}/{DATABASE_NAME}"
# Base = declarative_base()


engine = create_async_engine(DATABASE_URL, echo=False)

async_session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        # await conn.run_sync(Users_Base.metadata.drop_all)

        await conn.run_sync(Base.metadata.create_all)
        # await conn.run_sync(Users_Base.metadata.create_all)


async def get_db_session() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session_class() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()


if __name__ == "__main__":
    asyncio.run(init_models())
    print("¡Tablas creadas exitosamente!")
