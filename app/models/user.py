from typing import Optional

from pydantic import BaseModel
from pydantic import EmailStr
from pydantic import Field
from pydantic import model_validator
from tortoise import fields

from app.models.base import BaseDBModel
from app.utils import security


class User(BaseDBModel):
    id = fields.BigIntField(primary_key=True, db_index=True)
    email = fields.CharField(max_length=100, unique=True)
    first_name = fields.CharField(max_length=100)
    last_name = fields.CharField(max_length=100)
    password = fields.CharField(max_length=255)
    last_login = fields.DatetimeField(null=True)
    is_active = fields.BooleanField(default=False)
    is_staff = fields.BooleanField(default=False)
    is_superuser = fields.BooleanField(default=False)
    register_token = fields.CharField(max_length=50, null=True)
    invite_token = fields.CharField(max_length=255, null=True)
    stripe_customer_id = fields.CharField(max_length=50, null=True, unique=True)

    def full_name(self) -> str:
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    @classmethod
    async def get_by_email(cls, email: str) -> Optional['User']:
        query = cls.get_or_none(email=email.lower())
        user = await query
        return user

    @classmethod
    async def create(cls, user) -> 'User':
        hashed_password = security.get_password_hash(password=user.password)
        user.password = hashed_password
        user.email = user.email.lower()

        model = cls(**user.model_dump())
        await model.save()
        return model

    class PydanticMeta:
        computed = ['full_name']
        exclude = ['created_at', 'modified_at']

    class Meta:
        table = 'user'


class BaseUserInput(BaseModel):
    def create_update_dict(self):
        return self.model_dump(
            exclude_unset=True,
            exclude={'id', 'is_superuser', 'is_active'},
        )

    def create_update_dict_superuser(self):
        return self.model_dump(exclude_unset=True, exclude={'id'})


class UserCreate(BaseUserInput):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=40)
    invite_token: str = Field(default=None, max_length=40)
    register_token: str = Field(default=None, max_length=40)


class UserCreateAdmin(UserCreate):
    password: str | None
    is_active: bool | None = True
    is_superuser: bool | None = False
    stripe_customer_id: str | None = None


class UserUpdate(BaseUserInput):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)


class UpdatePassword(BaseModel):
    old_password: str = Field(min_length=8, max_length=40)
    new_password_1: str = Field(min_length=8, max_length=40)
    new_password_2: str = Field(min_length=8, max_length=40)

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'UpdatePassword':
        if self.new_password_1 != self.new_password_2:
            raise ValueError('passwords do not match')
        if self.new_password_1 == self.old_password:
            raise ValueError('new password should not be the same current')
        return self


class ResetPassword(BaseModel):
    new_password_1: str = Field(min_length=8, max_length=40)
    new_password_2: str = Field(min_length=8, max_length=40)

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'ResetPassword':
        if self.new_password_1 != self.new_password_2:
            raise ValueError('passwords do not match')
        return self


class UserOutputPublic(BaseModel):
    first_name: str | None
    last_name: str | None
    email: EmailStr | None = None


# User public output
class UserOutput(UserOutputPublic):
    id: int
    is_active: bool
    is_superuser: bool
    invite_token: str | None
    register_token: str | None
