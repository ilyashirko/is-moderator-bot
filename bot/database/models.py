from sqlalchemy import (
    Column, Integer, String, ForeignKey, Text, TIMESTAMP, text, BigInteger, UUID, Boolean, JSON, Date
)
from sqlalchemy.orm import relationship, declarative_base, backref, Mapped
from sqlalchemy.types import DECIMAL
import uuid

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True 
    
    id = Column(Integer, primary_key=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"), 
        onupdate=text("CURRENT_TIMESTAMP")
    )
    
class TelegramUser(BaseModel):
    __tablename__ = "telegram_users"

    telegram_id = Column(Text)
    username = Column(String(50))
    first_name = Column(String)

    confirmed = Column(Boolean, default=False)

    blocked_until = Column(Date)

    strikes = relationship(
        "Strikes",
        back_populates="telegram_user",
        cascade="all, delete-orphan",
    )

    bans = relationship(
        "Ban",
        back_populates="telegram_user",
        cascade="all, delete-orphan",
    )

class Strikes(BaseModel):
    __tablename__ = "strikes"

    telegram_user_id = Column(
        Integer,
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    message = Column(Text)

    telegram_user = relationship(
        "TelegramUser",
        back_populates="strikes",
    )

class Ban(BaseModel):
    __tablename__ = "bans"

    telegram_user_id = Column(
        Integer,
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        nullable=False,
    )

    reason = Column(Text)

    period = Column(Integer)

    telegram_user = relationship(
        "TelegramUser",
        back_populates="bans",
    )
    