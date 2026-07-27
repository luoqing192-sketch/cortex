"""Pydantic 请求体模型（响应多为直接 dict，贴合前端契约）。"""
from pydantic import BaseModel


class LoginBody(BaseModel):
    username: str
    password: str


class CreateUserBody(BaseModel):
    username: str
    password: str
    role: str = "user"


class PasswordBody(BaseModel):
    password: str


class PromptBody(BaseModel):
    name: str | None = None
    content: str | None = None
    description: str | None = ""
    is_active: bool | None = False


class PromptTestBody(BaseModel):
    promptContent: str
    testMessage: str


class ConversationCreateBody(BaseModel):
    title: str | None = None


class ChatBody(BaseModel):
    conversationId: int
    message: str


class WikiOrganizeBody(BaseModel):
    task: str | None = None


class WikiQueryBody(BaseModel):
    question: str
