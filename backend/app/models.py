from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Account(Base):
    """A Telegram userbot account (a real user account driven via MTProto)."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(32))
    session_enc: Mapped[Optional[str]] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(32), default="offline")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    groups: Mapped[list["Group"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class Prompt(Base):
    """A versioned system prompt that defines goals, rules, products and persona."""

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(Integer, default=1)
    system_text: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    groups: Mapped[list["Group"]] = relationship(back_populates="prompt")


class Group(Base):
    """A monitored Telegram group, optionally bound to a prompt."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), default=None)
    prompt_id: Mapped[Optional[int]] = mapped_column(ForeignKey("prompts.id"), default=None)
    mode: Mapped[str] = mapped_column(String(32), default="mention")  # mention | always | off
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    account: Mapped[Optional[Account]] = relationship(back_populates="groups")
    prompt: Mapped[Optional[Prompt]] = relationship(back_populates="groups")


class Message(Base):
    """Every inbound/outbound message observed by the userbot."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    telegram_message_id: Mapped[int] = mapped_column(Integer, default=0)
    sender_name: Mapped[str] = mapped_column(String(255), default="")
    direction: Mapped[str] = mapped_column(String(16))  # in | out
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Decision(Base):
    """An AI decision, stored for audit and live monitoring."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    message_id: Mapped[Optional[int]] = mapped_column(ForeignKey("messages.id"), default=None)
    action: Mapped[str] = mapped_column(String(32))  # reply | ignore | escalate
    reply_text: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Event(Base):
    """Structured application log surfaced to the UI."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(16), default="info")
    source: Mapped[str] = mapped_column(String(64), default="system")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
