from datetime import datetime

from tortoise import fields

from app.core.enums import SubscriptionStatus
from app.models.base import BaseDBModel
from app.models.base import InputSchema
from app.models.base import OutputSchema


class Subscription(BaseDBModel):
    user = fields.ForeignKeyField('app.User', on_delete=fields.CASCADE, related_name='user')
    subscription_price = fields.ForeignKeyField(
        'app.SubscriptionPrice', on_delete=fields.SET_NULL, null=True, blank=True
    )
    status = fields.CharEnumField(enum_type=SubscriptionStatus)
    current_period_start = fields.DatetimeField(null=True, blank=True)
    current_period_end = fields.DatetimeField(null=True, blank=True)
    trial_period_end = fields.DatetimeField(null=True, blank=True, default=None)
    expired_at = fields.DatetimeField(null=True, blank=True, default=None)
    canceled_at = fields.DatetimeField(null=True)
    stripe_subscription_id = fields.CharField(max_length=100, unique=True)

    class Meta:
        table = 'subscription'
        ordering = ['-created_at', 'id']


class SubscriptionInput(InputSchema):
    subscription_price_id: int
    success_url: str
    cancel_url: str
    # credits_to_purchase: int


class SubscriptionOutput(OutputSchema):
    user_id: int
    subscription_price_id: int
    status: SubscriptionStatus
    current_period_end: datetime | None
    trial_period_end: datetime | None
    expired_at: datetime | None
    stripe_subscription_id: str
