from typing import Any
from uuid import UUID

from pydantic import Field
from pydantic import Json
from tortoise import fields

from app.models.base import AuditOutputSchema
from app.models.base import BaseAuditedDBModel
from app.models.base import InputSchema
from app.models.document import DocumentMeta


class Policy(BaseAuditedDBModel):
    document = fields.ForeignKeyField('app.Document', unique=True, on_delete=fields.CASCADE)
    name = fields.CharField(max_length=255, null=True, blank=True)
    summary = fields.JSONField(blank=True, null=True)
    report = fields.JSONField(blank=True, null=True)
    type = fields.CharField(max_length=255, null=True, blank=True)

    class Meta:
        table = 'policy'


class PolicyCreate(InputSchema):
    name: str = Field(max_length=255)
    document_id: UUID = Field()


class PolicyOutput(AuditOutputSchema):
    document_id: UUID
    name: str | None
    type: str | None
    summary: Json | None
    report: Json | None


class PolicyOutputRelated(AuditOutputSchema):
    document: DocumentMeta
    name: str | None
    type: str | None
    summary: Any | None
    report: Any | None
