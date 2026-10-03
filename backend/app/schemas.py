from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Account ----
class AccountCreate(BaseModel):
    label: str
    phone: str


class AccountOut(ORMModel):
    id: int
    label: str
    phone: str
    status: str
    active: bool
    has_session: bool = False
    created_at: datetime


class CodeRequest(BaseModel):
    code: str


class PasswordRequest(BaseModel):
    password: str


# ---- Prompt ----
class PromptCreate(BaseModel):
    name: str
    system_text: str


class PromptUpdate(BaseModel):
    name: Optional[str] = None
    system_text: Optional[str] = None
    active: Optional[bool] = None


class PromptOut(ORMModel):
    id: int
    name: str
    version: int
    system_text: str
    active: bool
    created_at: datetime


# ---- Group ----
class GroupCreate(BaseModel):
    telegram_id: int
    title: str = ""
    account_id: Optional[int] = None
    prompt_id: Optional[int] = None
    mode: str = "mention"
    reply_scope: str = "relevant"
    max_replies_per_user_per_day: int = 2


class GroupUpdate(BaseModel):
    title: Optional[str] = None
    account_id: Optional[int] = None
    prompt_id: Optional[int] = None
    mode: Optional[str] = None
    reply_scope: Optional[str] = None
    max_replies_per_user_per_day: Optional[int] = None
    active: Optional[bool] = None


class GroupOut(ORMModel):
    id: int
    telegram_id: int
    title: str
    account_id: Optional[int]
    prompt_id: Optional[int]
    mode: str
    reply_scope: str
    max_replies_per_user_per_day: int
    active: bool
    created_at: datetime


# ---- Message / Decision ----
class MessageOut(ORMModel):
    id: int
    group_id: int
    sender_name: str
    direction: str
    text: str
    created_at: datetime


class DecisionOut(ORMModel):
    id: int
    group_id: int
    action: str
    reply_text: str
    reason: str
    created_at: datetime


class EventOut(ORMModel):
    id: int
    level: str
    source: str
    message: str
    created_at: datetime


# ---- Test / playground ----
class TestMessageRequest(BaseModel):
    group_id: int
    sender_name: str = "Client"
    text: str


class TestMessageResponse(BaseModel):
    action: str
    reply: str = ""
    reason: str = ""


# ---- Settings ----
class SettingsOut(BaseModel):
    app_name: str
    telegram_api_id: int
    telegram_api_configured: bool
    gemini_configured: bool
    gemini_model: str
    max_context_messages: int
    max_replies_per_hour: int
    max_replies_per_day: int


class SettingsUpdate(BaseModel):
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    reply_min_delay: Optional[float] = Field(default=None, ge=0)
    reply_max_delay: Optional[float] = Field(default=None, ge=0)
    max_replies_per_hour: Optional[int] = Field(default=None, ge=1)
    max_replies_per_day: Optional[int] = Field(default=None, ge=1)
