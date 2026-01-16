from database.models import TelegramUser, Strikes, Ban
from database import database, Database

from sqlalchemy import select, func
from sqlalchemy.orm import  joinedload
from datetime import datetime, timezone, timedelta


async def create_telegram_user(db: Database = database, **telegram_user_data):
    async with db.session() as session:
        user = TelegramUser(
            id=telegram_user_data["id"],
            first_name=telegram_user_data.get("first_name"),
            username=telegram_user_data.get("username"),
        )
        session.add(user)
        await session.flush()
        return user


async def confirm_telegram_user(telegram_user_id: int | str, db: Database = database):
    async with db.session() as session:
        user = await session.get(TelegramUser, telegram_user_id)
        user.confirmed = True
        session.flush()
        return user


async def get_telegram_user(telegram_user_id: int | str, db: Database = database):
    async with db.session() as session:
        stmt = select(TelegramUser) \
            .options(
                joinedload(TelegramUser.strikes),
            ) \
            .where(TelegramUser.id == telegram_user_id)
        result = await session.execute(stmt)
        user = result.unique().scalar_one_or_none()
        return user



async def create_strike_record(telegram_user_id: int | str, message: str, db: Database = database):
    async with db.session() as session:
        strike = Strikes(telegram_user_id=telegram_user_id, message=message)
        session.add(strike)
        await session.flush()
        return strike
    

async def count_strikes(telegram_user_id: int, db: Database = database, days: int = 30):
    async with db.session() as session:
        start_time = datetime.now(tz=timezone.utc) - timedelta(days=days)

        query = select(func.count(Strikes.id)).where(
            Strikes.telegram_user_id == telegram_user_id,
            Strikes.created_at >= start_time
        )

        result = await session.execute(query)
        count = result.scalar_one()
        return count
    
async def create_ban(telegram_user_id: int, reason: str, period: int, db: Database = database):
    async with db.session() as session:
        ban = Ban(telegram_user_id=telegram_user_id, reason=reason, period=period)
        session.add(ban)
        await session.flush()
        return ban
    
async def count_bans(telegram_user_id: int, db: Database = database):
    async with db.session() as session:
        query = select(func.count(Ban.id)).where(
            Ban.telegram_user_id == telegram_user_id,
            Ban.created_at >= datetime.now(tz=timezone.utc) - timedelta(days=365)
        )

        result = await session.execute(query)
        count = result.scalar_one()
        return count