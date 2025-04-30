import uuid
from decimal import Decimal

from fastapi.encoders import decimal_encoder
from pydantic import ConfigDict
from pydantic import EmailStr
from pydantic import Field
from tortoise import fields
from tortoise import models
from tortoise.contrib.pydantic import PydanticModel


class BaseDBModel(models.Model):
    id = fields.BigIntField(primary_key=True, db_index=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at', 'id']

    class PydanticMeta:
        exclude = ['created_at', 'modified_at']


class BaseSoftDelete(BaseDBModel):
    deleted_at = fields.DatetimeField(null=True)
    is_deleted = fields.BooleanField(default=False)

    class Meta:
        abstract = True

    class PydanticMeta:
        exclude = ['created_at', 'modified_at', 'deleted_at', 'is_deleted']


class BaseAuditedDBModel(BaseDBModel):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = fields.BigIntField()

    class Meta:
        abstract = True
        ordering = ['-created_at']

    class PydanticMeta:
        exclude = ['created_at', 'modified_at', 'created_by']


class InputSchema(PydanticModel, use_enum_values=True, from_attributes=True):
    def create_update_dict(self):
        return self.model_dump(
            exclude_unset=True,
            exclude={'id'},
        )

    def create_update_dict_superuser(self):
        return self.model_dump(exclude_unset=True, exclude={'id'})


class OutputSchema(PydanticModel, use_enum_values=True, from_attributes=True):
    id: int
    model_config = ConfigDict(json_encoders={Decimal: decimal_encoder})


class AuditOutputSchema(PydanticModel, use_enum_values=True, from_attributes=True):
    id: uuid.UUID


# Generic message
class Message(PydanticModel):
    message: str


# JSON payload containing access token
class Token(PydanticModel):
    access_token: str
    token_type: str = 'bearer'


class Email(PydanticModel):
    email: EmailStr = Field(max_length=100)


class Checkout(PydanticModel):
    session_id: str
    url: str
