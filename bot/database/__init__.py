from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from database.models import Base
import settings


class Database:
    def __init__(self, postgres_uri: str):
        self.engine = create_async_engine(
            postgres_uri, 
            echo=False, 
            future=True,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_pre_ping=True
        )
        self.session_factory = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def init_models(self, base = Base):
        """Создание таблиц при необходимости."""
        async with self.engine.begin() as conn:
            await conn.run_sync(base.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Контекстный менеджер для работы с сессией."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

database = Database(
    postgres_uri=(
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
)
