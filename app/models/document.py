from typing import Any

from pydantic import Field
from tortoise import fields

from app.core.enums import ExtractionStatus
from app.core.enums import ProductType
from app.models.base import AuditOutputSchema
from app.models.base import BaseAuditedDBModel
from app.models.base import InputSchema


class Document(BaseAuditedDBModel):
    name = fields.CharField(max_length=255)
    status = fields.CharEnumField(enum_type=ExtractionStatus)
    product = fields.CharEnumField(enum_type=ProductType)
    path = fields.CharField(max_length=255, default='/')
    url = fields.CharField(max_length=255, null=True, blank=True)
    extract_duration = fields.FloatField(null=True, blank=True)
    total_pages = fields.IntField(null=True, blank=True)
    size = fields.BigIntField(null=True, blank=True, help_text='Size of uploaded document')
    task_id = fields.CharField(
        max_length=100, null=True, blank=True, help_text=('ID referring to media processor queue task id')
    )
    vector_id = fields.CharField(max_length=100, null=True, blank=True, help_text=('ID referring to vector store'))
    summary_id = fields.CharField(
        max_length=100, null=True, blank=True, help_text=('ID referring to summary index store')
    )
    content = fields.JSONField(null=True, blank=True)

    class Meta:
        table = 'document'


class DocumentUpdate(InputSchema):
    extract_duration: float | None = Field(default=None, description='extract duration in ms')
    status: ExtractionStatus = Field(description='extraction status')
    total_pages: int | None = Field(default=None)
    vector_id: str | None = Field(default=None)
    summary_id: str | None = Field(default=None)
    content: list[str] | None = Field(default=None)


class DocumentOutput(AuditOutputSchema):
    name: str
    path: str
    status: ExtractionStatus
    url: str | None
    extract_duration: float | None
    total_pages: int | None
    size: int | None
    vector_id: str | None
    summary_id: str | None


class DocumentAdminOutput(DocumentOutput):
    product: ProductType
    content: Any | None


class DocumentMeta(AuditOutputSchema):
    name: str
    status: ExtractionStatus
    vector_id: str | None
    summary_id: str | None
    content: Any | None
