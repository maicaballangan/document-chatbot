from datetime import datetime
from datetime import timedelta
from decimal import Decimal

import stripe

from app.core.config import settings
from app.core.enums import InvoiceStatus
from app.core.enums import PaymentStatus
from app.core.enums import SubscriptionStatus
from app.models.invoice import Invoice
from app.models.subscription import Subscription

BASE_URL = f'{settings.API_V1_STR}/webhooks/stripe'


async def test_subscription_created_webhook(client, normal_user, subscription_price_mock, monkeypatch):
    # Mock the stripe.Webhook.construct_event method
    def mock_construct_event(*args, **kwargs):
        current_time = int(datetime.now().timestamp())
        period_end = int((datetime.now() + timedelta(days=30)).timestamp())

        return {
            'type': 'customer.subscription.created',
            'data': {
                'object': {
                    'id': 'sub_test123',
                    'customer': normal_user.stripe_customer_id,
                    'status': 'active',
                    'current_period_start': current_time,
                    'current_period_end': period_end,
                    'plan': {
                        'id': subscription_price_mock.stripe_price_id,
                    },
                }
            },
        }

    monkeypatch.setattr(stripe.Webhook, 'construct_event', mock_construct_event)

    # Mock the stripe.Subscription.modify method
    monkeypatch.setattr(stripe.Subscription, 'modify', lambda *args, **kwargs: None)
    response = await client.post(BASE_URL, headers={'stripe-signature': 'test_signature'})

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['status'] == 'success'
    assert response_data['subscription_id'] == 'sub_test123'

    # Verify database records
    subscription = await Subscription.get_or_none(stripe_subscription_id='sub_test123')
    assert subscription is not None
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.user_id == normal_user.id
    assert subscription.subscription_price_id == subscription_price_mock.id


async def test_subscription_updated_webhook(client, normal_user, subscription_price_mock, monkeypatch):
    # Create a subscription first to update
    current_time = int(datetime.now().timestamp())
    period_end = int((datetime.now() + timedelta(days=30)).timestamp())
    subscription = await Subscription.create(
        user=normal_user,
        stripe_subscription_id='sub_test456',
        subscription_price=subscription_price_mock,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=datetime.fromtimestamp(current_time),
        current_period_end=datetime.fromtimestamp(period_end),
    )

    # Mock the webhook event
    def mock_construct_event(*args, **kwargs):
        new_period_end = int((datetime.now() + timedelta(days=60)).timestamp())

        return {
            'type': 'customer.subscription.updated',
            'data': {
                'object': {
                    'id': 'sub_test456',
                    'customer': normal_user.stripe_customer_id,
                    'status': 'past_due',
                    'current_period_start': current_time,
                    'current_period_end': new_period_end,
                    'plan': {
                        'id': subscription_price_mock.stripe_price_id,
                    },
                }
            },
        }

    monkeypatch.setattr(stripe.Webhook, 'construct_event', mock_construct_event)
    response = await client.post(BASE_URL, headers={'stripe-signature': 'test_signature'})

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['status'] == 'success'
    assert response_data['subscription_id'] == 'sub_test456'

    # Verify database records
    updated_subscription = await Subscription.get(stripe_subscription_id='sub_test456')
    assert updated_subscription.status == SubscriptionStatus.PAST_DUE
    assert updated_subscription.current_period_end > subscription.current_period_end

    await subscription.delete()


async def test_subscription_deleted_webhook(client, normal_user, subscription_price_mock, monkeypatch):
    # Create a subscription first to delete
    current_time = int(datetime.now().timestamp())
    period_end = int((datetime.now() + timedelta(days=30)).timestamp())
    subscription = await Subscription.create(
        user=normal_user,
        stripe_subscription_id='sub_test789',
        subscription_price=subscription_price_mock,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=datetime.fromtimestamp(current_time),
        current_period_end=datetime.fromtimestamp(period_end),
    )

    # Mock the webhook event
    def mock_construct_event(*args, **kwargs):
        canceled_at = int(datetime.now().timestamp())

        return {
            'type': 'customer.subscription.deleted',
            'data': {
                'object': {
                    'id': 'sub_test789',
                    'customer': normal_user.stripe_customer_id,
                    'status': 'canceled',
                    'canceled_at': canceled_at,
                    'current_period_start': current_time,
                    'current_period_end': period_end,
                    'plan': {
                        'id': subscription_price_mock.stripe_price_id,
                    },
                }
            },
        }

    monkeypatch.setattr(stripe.Webhook, 'construct_event', mock_construct_event)
    response = await client.post(BASE_URL, headers={'stripe-signature': 'test_signature'})

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['status'] == 'success'
    assert response_data['subscription_id'] == 'sub_test789'

    # Verify database records
    deleted_subscription = await Subscription.get(stripe_subscription_id='sub_test789')
    assert deleted_subscription.status == SubscriptionStatus.CANCELED
    assert deleted_subscription.canceled_at is not None

    await subscription.delete()


async def test_invoice_created_webhook(client, normal_user, monkeypatch):
    # Mock the webhook event
    def mock_construct_event(*args, **kwargs):
        due_date = int((datetime.now() + timedelta(days=7)).timestamp())

        return {
            'type': 'invoice.created',
            'data': {
                'object': {
                    'id': 'in_test123',
                    'customer': normal_user.stripe_customer_id,
                    'status': 'open',
                    'amount_due': 1999,  # $19.99 in cents
                    'currency': 'usd',
                    'due_date': due_date,
                    'status_transitions': {},
                }
            },
        }

    monkeypatch.setattr(stripe.Webhook, 'construct_event', mock_construct_event)
    response = await client.post(BASE_URL, headers={'stripe-signature': 'test_signature'})

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['status'] == 'success'
    assert response_data['invoice_id'] == 'in_test123'

    # Verify database records
    invoice = await Invoice.get_or_none(stripe_invoice_id='in_test123')
    assert invoice is not None
    assert invoice.status == InvoiceStatus.OPEN
    assert invoice.payment_status == PaymentStatus.UNPAID
    assert invoice.amount == Decimal('19.99')
    assert invoice.currency == 'usd'
    assert invoice.user_id == normal_user.id

    await invoice.delete()


async def test_invoice_paid_webhook(client, normal_user, monkeypatch):
    # Mock the webhook event
    def mock_construct_event(*args, **kwargs):
        current_time = int(datetime.now().timestamp())

        return {
            'type': 'invoice.paid',
            'data': {
                'object': {
                    'id': 'in_test456',
                    'customer': normal_user.stripe_customer_id,
                    'status': 'paid',
                    'amount_due': 1999,  # $19.99 in cents
                    'currency': 'usd',
                    'status_transitions': {'paid_at': current_time},
                }
            },
        }

    monkeypatch.setattr(stripe.Webhook, 'construct_event', mock_construct_event)

    response = await client.post(BASE_URL, headers={'stripe-signature': 'test_signature'})

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['status'] == 'success'
    assert response_data['invoice_id'] == 'in_test456'

    # Verify database records
    invoice = await Invoice.get_or_none(stripe_invoice_id='in_test456')
    assert invoice is not None
    assert invoice.status == InvoiceStatus.PAID
    assert invoice.payment_status == PaymentStatus.SUCCESS
    assert invoice.amount == Decimal('19.99')
    assert invoice.currency == 'usd'
    assert invoice.paid_at is not None

    await invoice.delete()


async def test_invoice_payment_failed_webhook(client, normal_user, monkeypatch):
    # Create an invoice first
    invoice = await Invoice.create(
        user=normal_user,
        stripe_invoice_id='in_test789',
        status=InvoiceStatus.OPEN,
        payment_status=PaymentStatus.UNPAID,
        amount=29.99,
        currency='usd',
    )

    # Mock the webhook event
    def mock_construct_event(*args, **kwargs):
        next_attempt = int((datetime.now() + timedelta(days=3)).timestamp())

        return {
            'type': 'invoice.payment_failed',
            'data': {
                'object': {
                    'id': 'in_test789',
                    'customer': normal_user.stripe_customer_id,
                    'status': 'open',
                    'attempt_count': 1,
                    'next_payment_attempt': next_attempt,
                }
            },
        }

    monkeypatch.setattr(stripe.Webhook, 'construct_event', mock_construct_event)
    response = await client.post(BASE_URL, headers={'stripe-signature': 'test_signature'})

    assert response.status_code == 200
    response_data = response.json()
    assert response_data['status'] == 'success'
    assert response_data['invoice_id'] == 'in_test789'

    # Verify database records
    updated_invoice = await Invoice.get(stripe_invoice_id='in_test789')
    assert updated_invoice.payment_status == PaymentStatus.FAILED
    assert updated_invoice.attempt_count == 1
    assert updated_invoice.next_payment_attempt is not None

    await invoice.delete()


async def test_invoice_payment_action_required_webhook(client, normal_user, monkeypatch):
    # Create an invoice first
    invoice = await Invoice.create(
        user=normal_user,
        stripe_invoice_id='in_testABC',
        status=InvoiceStatus.OPEN,
        payment_status=PaymentStatus.UNPAID,
        amount=39.99,
        currency='usd',
    )

    # Mock the webhook event
    def mock_construct_event(*args, **kwargs):
        return {
            'type': 'invoice.payment_action_required',
            'data': {
                'object': {
                    'id': 'in_testABC',
                    'customer': normal_user.stripe_customer_id,
                    'status': 'open',
                    'payment_intent': 'pi_test123',
                }
            },
        }

    monkeypatch.setattr(stripe.Webhook, 'construct_event', mock_construct_event)

    response = await client.post(BASE_URL, headers={'stripe-signature': 'test_signature'})
    assert response.status_code == 200
    response_data = response.json()
    assert response_data['status'] == 'success'
    assert response_data['invoice_id'] == 'in_testABC'

    # Verify database records
    updated_invoice = await Invoice.get(stripe_invoice_id='in_testABC')
    assert updated_invoice.payment_status == PaymentStatus.ACTION_REQUIRED

    await invoice.delete()


async def test_invalid_signature(client, monkeypatch):
    # Mock the stripe.Webhook.construct_event to raise error
    def mock_construct_event(*args, **kwargs):
        raise stripe.SignatureVerificationError('Invalid signature', 'sig_header')

    monkeypatch.setattr(stripe.Webhook, 'construct_event', mock_construct_event)

    response = await client.post(BASE_URL, headers={'stripe-signature': 'test_signature'})
    assert response.status_code == 400
    assert 'Invalid signature' in response.json()['detail']


async def test_missing_signature(client):
    response = await client.post(
        BASE_URL,
    )
    assert response.status_code == 400
    assert 'Stripe signature is missing' in response.json()['detail']


async def test_unhandled_event_type(client, monkeypatch):
    # Mock the webhook event with an unhandled type

    def mock_construct_event(*args, **kwargs):
        return {'type': 'charge.succeeded', 'data': {'object': {'id': 'ch_test123'}}}

    monkeypatch.setattr(stripe.Webhook, 'construct_event', mock_construct_event)
    response = await client.post(BASE_URL, headers={'stripe-signature': 'test_signature'})

    # Even for unhandled event types, we should return 200 OK
    assert response.status_code == 200
