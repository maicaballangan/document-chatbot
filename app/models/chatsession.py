from uuid import UUID

from pydantic import Field
from tortoise import fields

from app.core.enums import ProductType
from app.models.base import AuditOutputSchema
from app.models.base import BaseAuditedDBModel
from app.models.base import InputSchema
from app.models.user import UserOutputPublic


class ChatSession(BaseAuditedDBModel):
    name = fields.CharField(max_length=50, null=True, blank=True)
    documents_json = fields.JSONField()
    product = fields.CharEnumField(enum_type=ProductType)
    product_id = fields.UUIDField(null=True, blank=True)  # ID reference for product
    shared_with = fields.ManyToManyField(
        'app.User', related_name='session_viewers', null=True, blank=True, on_delete=fields.NO_ACTION
    )

    class Meta:
        table = 'chat_session'


class ChatSessionInput(InputSchema):
    name: str | None = Field(min_length=1)
    product_id: UUID | None = Field(default=None, description='policy_id or discovery_id reference')
    document_ids: list[UUID] | None = Field(default=None, description='document_id list for this chat session')


class ChatSessionOutput(AuditOutputSchema):
    name: str | None
    product_id: UUID | None
    documents_json: list[dict]


class ChatSessionAdminOutput(ChatSessionOutput):
    product: ProductType


class ChatSessionRelatedOutput(AuditOutputSchema):
    name: str | None
    product_id: UUID | None
    shared_with: list[UserOutputPublic] | None


class ChatSessionMeta(AuditOutputSchema):
    name: str | None
    documents_json: dict
