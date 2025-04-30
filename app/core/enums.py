from enum import StrEnum


class ExtractionStatus(StrEnum):
    PENDING = 'pending'
    SUCCESS = 'success'
    INVALID = 'invalid'
    FAILED = 'failed'
    FAILED_QUEUE = 'failed_queue'  # can retry again


class ProductType(StrEnum):
    GENERAL = 'general'
    POLICY = 'policy'
    DISCOVERY = 'discovery'


class ChatRole(StrEnum):
    USER = 'user'
    ASSISTANT = 'assistant'


class HelpfulQuestionType(StrEnum):
    GENERAL = 'general'
    POLICY = 'policy'


class BillingCycle(StrEnum):
    MONTHLY = 'monthly'
    ANNUAL = 'annual'


class SubscriptionStatus(StrEnum):
    TRIAL = 'trial'
    ACTIVE = 'active'
    CANCELED = 'canceled'
    INCOMPLETE = 'incomplete'
    INCOMPLETE_EXPIRED = 'expired'
    PAST_DUE = 'past_due'
    UNPAID = 'unpaid'
    PAUSED = 'paused'


class PaymentStatus(StrEnum):
    SUCCESS = 'success'
    FAILED = 'failed'
    UNPAID = 'unpaid'
    ACTION_REQUIRED = 'action_required'


class InvoiceStatus(StrEnum):
    PAID = 'paid'
    FAILED = 'failed'
    DRAFT = 'draft'
    OPEN = 'open'
    UNCOLLECTIBLE = 'uncollectible'
    VOID = 'void'
