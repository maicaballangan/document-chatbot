from tortoise import fields

from app.core.enums import InvoiceStatus
from app.core.enums import PaymentStatus
from app.models.base import BaseDBModel


class Invoice(BaseDBModel):
    user = fields.ForeignKeyField('app.User', related_name='invoices')  # removed delete cascade
    stripe_invoice_id = fields.CharField(max_length=255, unique=True)
    attempt_count = fields.IntField(default=1)
    next_payment_attempt = fields.DatetimeField(null=True)
    amount = fields.DecimalField(max_digits=10, decimal_places=2)
    currency = fields.CharField(max_length=3, default='USD')
    status = fields.CharEnumField(enum_type=InvoiceStatus)
    payment_status = fields.CharEnumField(enum_type=PaymentStatus)
    paid_at = fields.DatetimeField(null=True)

    class Meta:
        table = 'invoice'
