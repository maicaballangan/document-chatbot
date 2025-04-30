from pydantic import Field
from tortoise import fields

from app.models.base import BaseDBModel
from app.models.base import InputSchema
from app.models.base import OutputSchema


class SubscriptionPlan(BaseDBModel):
    name = fields.CharField(max_length=100, unique=True)
    credits = fields.IntField(default=0, null=True)  # if purchase annually, this will be each month earned
    document_limit = fields.IntField(null=True)  # same as above
    question_limit = fields.IntField(null=True)  # same as above
    storage_limit = fields.BigIntField(null=True)
    descriptions = fields.JSONField(null=True, blank=True)
    is_consular = fields.BooleanField(default=False)
    trial_period = fields.IntField(default=None, null=True)  # number days of trial
    document_size_limit = fields.BigIntField(null=True)
    ocr_support = fields.BooleanField(default=False)
    chat_with_files = fields.BooleanField(default=True)
    chat_with_folders = fields.BooleanField(default=False)
    invite_team = fields.BooleanField(default=False)
    maximum_member = fields.IntField(null=True)
    policy_analyzer_report_card = fields.BooleanField(default=False)
    discovery_tool_interrogatories = fields.BooleanField(default=False)
    customer_support_email = fields.BooleanField(default=False)
    customer_support_phone = fields.BooleanField(default=False)
    support_turnaround = fields.IntField(null=True)
    support_mycase = fields.BooleanField(default=False)
    stripe_product_id = fields.CharField(max_length=50, unique=True)

    class Meta:
        table = 'subscription_plan'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class SubscriptionPlanCreate(InputSchema):
    name: str
    credits: int | None = Field(default=0)
    document_limit: int | None = Field(default=0)
    question_limit: int | None = Field(default=0)
    storage_limit: int | None = Field(default=0)
    descriptions: list | None = Field(default=None)
    is_consular: bool | None = Field(default=False)
    trial_period: int | None = Field(default=None)
    document_size_limit: int | None = Field(default=False)
    ocr_support: bool | None = Field(default=False)
    chat_with_files: bool | None = Field(default=True)
    chat_with_folders: bool | None = Field(default=False)
    invite_team: bool | None = Field(default=False)
    maximum_member: int | None = Field(default=None)
    policy_analyzer_report_card: bool | None = Field(default=False)
    discovery_tool_interrogatories: bool | None = Field(default=False)
    customer_support_email: bool | None = Field(default=False)
    customer_support_phone: bool | None = Field(default=False)
    support_turnaround: int | None = Field(default=None)
    support_mycase: bool | None = Field(default=False)


class SubscriptionPlanUpdate(InputSchema):
    name: str
    credits: int | None = Field(default=0)
    document_limit: int | None = Field(default=0)
    question_limit: int | None = Field(default=0)
    storage_limit: int | None = Field(default=0)
    descriptions: list | None = Field(default=None)
    is_consular: bool | None = Field(default=False)
    trial_period: int | None = Field(default=None)
    document_size_limit: int | None = Field(default=False)
    ocr_support: bool | None = Field(default=False)
    chat_with_files: bool | None = Field(default=True)
    chat_with_folders: bool | None = Field(default=False)
    invite_team: bool | None = Field(default=False)
    maximum_member: int | None = Field(default=None)
    policy_analyzer_report_card: bool | None = Field(default=False)
    discovery_tool_interrogatories: bool | None = Field(default=False)
    customer_support_email: bool | None = Field(default=False)
    customer_support_phone: bool | None = Field(default=False)
    support_turnaround: int | None = Field(default=None)
    support_mycase: bool | None = Field(default=False)


class SubscriptionPlanOutput(OutputSchema):
    name: str
    credits: int
    document_limit: int
    question_limit: int
    storage_limit: int
    descriptions: list | None
    is_consular: bool
    trial_period: int | None
    document_size_limit: int | None
    ocr_support: bool
    chat_with_files: bool
    chat_with_folders: bool | None
    invite_team: bool | None
    maximum_member: int | None
    policy_analyzer_report_card: bool | None
    discovery_tool_interrogatories: bool | None
    customer_support_email: bool | None
    customer_support_phone: bool | None
    support_turnaround: int | None
    support_mycase: bool | None
