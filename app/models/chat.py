from typing import Any
from uuid import UUID

from pydantic import Json
from tortoise import fields

from app.core.enums import ChatRole
from app.core.enums import HelpfulQuestionType
from app.models.base import AuditOutputSchema
from app.models.base import BaseAuditedDBModel
from app.models.base import BaseDBModel
from app.models.base import InputSchema


class Chat(BaseAuditedDBModel):
    created_by = fields.BigIntField(null=True, blank=True)  # override created_by nullable
    session = fields.ForeignKeyField('app.ChatSession', on_delete=fields.CASCADE)
    content = fields.TextField()
    role = fields.CharEnumField(enum_type=ChatRole)
    response_to = fields.UUIDField(null=True, blank=True)
    is_liked = fields.BooleanField(null=True, blank=True)
    is_bookmarked = fields.BooleanField(null=True, blank=True)
    bookmark_name = fields.TextField(null=True, blank=True)
    source_info = fields.JSONField(null=True, blank=True)

    class Meta:
        table = 'chat'


class HelpfulQuestion(BaseDBModel):
    question = fields.CharField(max_length=255)
    answer = fields.CharField(max_length=255, default='')
    status = fields.CharEnumField(enum_type=HelpfulQuestionType)


class ChatCreateInput(InputSchema):
    content: str
    response_to: UUID | None


class ChatAgentCreateInput(InputSchema):
    session_id: UUID
    content: str
    response_to: UUID
    role: ChatRole
    source_info: Json


class ChatBookmarkUpdate(InputSchema):
    is_bookmarked: bool | None


class ChatLikeUpdate(InputSchema):
    is_liked: bool | None


class ChatOutput(AuditOutputSchema):
    created_by: int | None
    session_id: UUID
    content: str
    role: ChatRole
    response_to: UUID | None
    is_liked: bool | None
    is_bookmarked: bool | None
    bookmark_name: str | None
    source_info: Any | None
