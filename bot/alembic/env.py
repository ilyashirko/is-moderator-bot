from sqlalchemy import create_engine
from alembic import context
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def get_database_url():
    """Лениво получаем URL без инициализации всей БД"""
    import settings
    return (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )

def run_migrations_online() -> None:
    from database.models import Base
    
    engine = create_engine(get_database_url())
    
    with engine.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=Base.metadata
        )
        
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()