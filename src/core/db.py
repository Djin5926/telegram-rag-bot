"""Асинхронный движок и фабрика сессий SQLAlchemy.

Единая точка создания engine на процесс; сессии выдаются через
`async with session_maker() as session`.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.config import Settings

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def init_engine(settings: Settings) -> async_sessionmaker[AsyncSession]:
    """Создаёт engine и фабрику сессий (идемпотентно)."""
    global _engine, _session_maker
    if _session_maker is not None:
        return _session_maker
    _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    _session_maker = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_maker


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    if _session_maker is None:
        raise RuntimeError("Движок БД не инициализирован: сначала вызовите init_engine()")
    return _session_maker


async def dispose_engine() -> None:
    """Аккуратно закрывает пул соединений при остановке приложения."""
    global _engine, _session_maker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_maker = None
