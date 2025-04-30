from decimal import Decimal

from iso4217 import Currency
from pydantic import Field
from tortoise import fields

from app.core.enums import BillingCycle
from app.models.base import BaseSoftDelete
from app.models.base import InputSchema
from app.models.base import OutputSchema


class SubscriptionPrice(BaseSoftDelete):
    subscription_plan = fields.ForeignKeyField(
        'app.SubscriptionPlan', related_name='subscription_plan', on_delete=fields.CASCADE
    )
    stripe_price_id = fields.CharField(max_length=50, unique=True)  # This is the Stripe price ID
    billing_cycle = fields.CharEnumField(enum_type=BillingCycle)
    amount = fields.DecimalField(max_digits=10, decimal_places=2)  # The cost of this plan
    currency = fields.CharEnumField(enum_type=Currency)

    class Meta:
        table = 'subscription_price'
        ordering = ['amount']


class SubscriptionPriceCreate(InputSchema):
    subscription_plan_id: int
    billing_cycle: BillingCycle
    amount: Decimal = Field(ge=1.00, decimal_places=2)
    currency: Currency = Field(default='USD')


class SubscriptionPriceUpdate(InputSchema):
    amount: Decimal = Field(ge=1.00, decimal_places=2)


class SubscriptionPriceOutput(OutputSchema):
    subscription_plan_id: int
    billing_cycle: BillingCycle
    amount: Decimal = Field(ge=1.00, decimal_places=2)
    currency: Currency = Field(default='USD')
