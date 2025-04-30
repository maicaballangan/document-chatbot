import logging
from datetime import datetime
from http import HTTPStatus

import stripe
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.enums import InvoiceStatus
from app.core.enums import PaymentStatus
from app.core.enums import SubscriptionStatus
from app.models.invoice import Invoice
from app.models.subscription import Subscription
from app.models.subscription_price import SubscriptionPrice
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# Subscription status mapping from Stripe to our enum
SUBSCRIPTION_STATUS_MAPPING = {
    'trialing': SubscriptionStatus.TRIAL,
    'active': SubscriptionStatus.ACTIVE,
    'canceled': SubscriptionStatus.CANCELED,
    'incomplete': SubscriptionStatus.INCOMPLETE,
    'incomplete_expired': SubscriptionStatus.INCOMPLETE_EXPIRED,
    'past_due': SubscriptionStatus.PAST_DUE,
    'unpaid': SubscriptionStatus.UNPAID,
    'paused': SubscriptionStatus.PAUSED,
}


async def verify_stripe_signature(request: Request, stripe_signature: str = Header(None)):
    """Verify that the webhook request came from Stripe."""
    if not stripe_signature:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Stripe signature is missing')

    try:
        # Read the request body
        payload = await request.body()
        event = stripe.Webhook.construct_event(payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET)
        return event
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))
    except stripe.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))


@router.post('/stripe', status_code=HTTPStatus.OK)
async def stripe_webhook(event: dict = Depends(verify_stripe_signature)):
    """Handle Stripe webhook events related to subscriptions and payments."""
    event_type = event['type']
    logger.info(f'Received Stripe event: {event_type}')

    try:
        event_type = event['type']
        # Handle subscription events
        if event_type.startswith('customer.subscription'):
            return await handle_subscription_event(event)

        # Handle invoice events
        elif event_type.startswith('invoice'):
            return await handle_invoice_event(event)

        # TODO Handle payment intent events
        # elif event_type.startswith("payment_intent"):
        #    return await handle_payment_intent_event(event)

        else:
            logger.info(f'Unhandled event type: {event_type}')

    except Exception:
        logger.exception(f'Error processing webhook event type {event_type}')
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail='Error processing webhook')


async def handle_subscription_event(event: dict):
    """Process subscription-related webhook events."""
    event_type = event['type']
    subscription = event['data']['object']
    customer_id = subscription.get('customer')
    subscription_id = subscription.get('id')
    status = subscription.get('status')

    # Map the Stripe status to your application's status
    mapped_status = SUBSCRIPTION_STATUS_MAPPING.get(status, status)

    if event_type == 'customer.subscription.created':
        await handle_subscription_created(customer_id, subscription_id, mapped_status, subscription)
    elif event_type == 'customer.subscription.updated':
        await handle_subscription_updated(customer_id, subscription_id, mapped_status, subscription)
    elif event_type == 'customer.subscription.deleted':
        await handle_subscription_deleted(customer_id, subscription_id, subscription)

    return JSONResponse(
        content={
            'status': 'success',
            'message': f'Processed {event_type}',
            'customer_id': customer_id,
            'subscription_id': subscription_id,
            # "status": mapped_status
        }
    )


async def handle_subscription_created(
    customer_id: str, subscription_id: str, status: SubscriptionStatus, subscription_data: dict
):
    """Handle subscription creation events."""
    logger.info(f'Subscription created: {subscription_id} for customer {customer_id} with status {status}')

    # Find the user associated with this Stripe customer ID
    user = await User.get_or_none(stripe_customer_id=customer_id)
    if not user:
        logger.warning(f'User not found for Stripe customer ID: {customer_id}')
        return

    # If a different plan is active, cancel the current subscription at the end of current billing period
    active_subscription = await Subscription.get_or_none(
        user_id=user.id, status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE]
    )

    if active_subscription:
        stripe.Subscription.modify(active_subscription.stripe_subscription_id, cancel_at_period_end=True)

    # Get updated plan details
    stripe_price_id = subscription_data['plan']['id']
    subscription_price = await SubscriptionPrice.get_or_none(stripe_price_id=stripe_price_id)
    if subscription_price is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='subscription price plan not found',
        )

    subscription = await Subscription.get_or_none(stripe_subscription_id=subscription_id)
    if subscription is None:
        # Create a new subscription record
        subscription = await Subscription.create(
            user=user,
            stripe_subscription_id=subscription_id,
            subscription_price_id=subscription_price.id,
            status=status.value,
            current_period_start=datetime.fromtimestamp(subscription_data.get('current_period_start', 0)),
            current_period_end=datetime.fromtimestamp(subscription_data.get('current_period_end', 0)),
        )
    return subscription
    # Update user access level based on plan (implementation depends on your business logic)
    # await update_user_access_level(user.id, plan_id)


async def handle_subscription_updated(
    customer_id: str, subscription_id: str, status: SubscriptionStatus, subscription_data: dict
):
    """Handle subscription update events."""
    logger.info(f'Subscription updated: {subscription_id} for customer {customer_id} with status {status}')

    subscription = await Subscription.get_or_none(stripe_subscription_id=subscription_id)
    if not subscription:
        logger.warning(f'Subscription not found for ID: {subscription_id}')
        subscription = await handle_subscription_created(customer_id, subscription_id, status, subscription_data)

    # Update the subscription
    subscription.status = status
    subscription.current_period_start = datetime.fromtimestamp(subscription_data.get('current_period_start', 0))
    subscription.current_period_end = datetime.fromtimestamp(subscription_data.get('current_period_end', 0))

    await subscription.save()
    # If plan changed, update user access
    # if plan_id != db_subscription.plan_id:
    #    user = await db_subscription.user
    #    await update_user_access_level(user.id, plan_id)


async def handle_subscription_deleted(customer_id: str, subscription_id: str, subscription_data: dict):
    """Handle subscription deletion events."""
    logger.info(f'Subscription deleted: {subscription_id} for customer {customer_id}')

    # Find the subscription record in your database
    subscription = await Subscription.get_or_none(stripe_subscription_id=subscription_id)
    if not subscription:
        logger.warning(f'Subscription not found for ID: {subscription_id}')
        return

    # Update subscription status
    subscription.status = SubscriptionStatus.CANCELED
    if subscription_data.get('canceled_at'):
        subscription.canceled_at = datetime.fromtimestamp(subscription_data.get('canceled_at'))

    await subscription.save()
    # Update user access
    # user = await db_subscription.user
    # await revoke_user_access(user.id)


async def handle_invoice_event(event: dict):
    """Process invoice-related webhook events."""
    event_type = event['type']
    invoice = event['data']['object']
    customer_id = invoice.get('customer')
    invoice_id = invoice.get('id')
    status = invoice.get('status')

    logger.info(f'Processing invoice event: {event_type} with status {status}')

    # Find the user associated with this Stripe customer ID
    user = await User.get_or_none(stripe_customer_id=customer_id)
    if not user:
        logger.warning(f'User not found for Stripe customer ID: {customer_id}')
        return JSONResponse(content={'status': 'warning', 'message': 'User not found'})

    # Map invoice status to your application status
    invoice_status = InvoiceStatus.DRAFT
    payment_status = PaymentStatus.UNPAID

    if status == 'open':
        invoice_status = InvoiceStatus.OPEN
    elif status == 'paid':
        invoice_status = InvoiceStatus.PAID
        payment_status = PaymentStatus.SUCCESS
    elif status == 'uncollectible':
        invoice_status = InvoiceStatus.UNCOLLECTIBLE
        payment_status = PaymentStatus.FAILED
    elif status == 'void':
        invoice_status = InvoiceStatus.VOID

    # Handle specific invoice events
    if event_type == 'invoice.created':
        await handle_invoice_created(user, invoice_id, invoice_status, payment_status, invoice)

    elif event_type == 'invoice.paid':
        await handle_invoice_paid(user, invoice_id, invoice)

    elif event_type == 'invoice.payment_failed':
        await handle_invoice_payment_failed(user, invoice_id, invoice)

    elif event_type == 'invoice.payment_action_required':
        await handle_invoice_payment_action_required(user, invoice_id, invoice)

    # Return success response
    return JSONResponse(
        content={
            'status': 'success',
            'message': f'Processed {event_type}',
            'customer_id': customer_id,
            'invoice_id': invoice_id,
            # "status": status
        }
    )


async def handle_invoice_created(
    user: User, invoice_id: str, invoice_status: InvoiceStatus, payment_status: PaymentStatus, invoice_data: dict
):
    """Handle invoice creation events."""
    # Get or create invoice
    invoice = await Invoice.get_or_none(stripe_invoice_id=invoice_id)

    if not invoice:
        # Create new invoice record
        invoice = await Invoice.create(
            user=user,
            stripe_invoice_id=invoice_id,
            status=invoice_status,
            payment_status=payment_status,
            amount=invoice_data.get('amount_due', 0) / 100,  # Convert cents to dollars/currency unit
            currency=invoice_data.get('currency', 'usd'),
            paid_at=datetime.fromtimestamp(invoice_data.get('status_transitions', {}).get('paid_at', 0)),
            due_date=datetime.fromtimestamp(invoice_data.get('due_date', 0)) if invoice_data.get('due_date') else None,
            # invoice_pdf=invoice_data.get("invoice_pdf") # Todo when to store blob files
        )
        logger.info(f'Invoice created: {invoice_id} for user {user.id} with status {invoice_status.value}')


async def handle_invoice_paid(user: User, invoice_id: str, invoice_data: dict):
    """Handle invoice paid events."""
    logger.info(f'Invoice paid: {invoice_id} for user {user.id}')

    invoice = await Invoice.get_or_none(stripe_invoice_id=invoice_id)
    if not invoice:
        # Create invoice if it doesn't exist
        invoice = await handle_invoice_created(
            user, invoice_id, InvoiceStatus.PAID, PaymentStatus.SUCCESS, invoice_data
        )
    else:
        # Update existing invoice
        invoice.status = InvoiceStatus.PAID
        invoice.payment_status = PaymentStatus.SUCCESS
        invoice.paid_at = datetime.fromtimestamp(invoice_data.get('status_transitions', {}).get('paid_at', 0))
        await invoice.save()
        logger.info(f'Invoice paid: {invoice_id} for user {user.id}')


async def handle_invoice_payment_failed(user: User, invoice_id: str, invoice_data: dict):
    """Handle invoice payment failure events."""
    logger.info(f'Invoice payment failed: {invoice_id} for user {user.id}')

    invoice = await Invoice.get_or_none(stripe_invoice_id=invoice_id)
    if not invoice:
        logger.warning(f'Invoice not found for user {user.id} with invoice ID: {invoice_id}')
        return

    invoice.payment_status = PaymentStatus.FAILED
    invoice.attempt_count = invoice_data.get('attempt_count', 0)
    invoice.next_payment_attempt = (
        datetime.fromtimestamp(invoice_data.get('next_payment_attempt', 0))
        if invoice_data.get('next_payment_attempt')
        else None
    )
    await invoice.save()

    # You might want to notify the user about the failed payment
    # await send_payment_failed_notification(user.email, db_invoice)


async def handle_invoice_payment_action_required(user: User, invoice_id: str, invoice_data: dict):
    """Handle invoice payment action required events."""
    logger.info(f'Invoice payment action required: {invoice_id} for user {user.id}')

    invoice = await Invoice.get_or_none(stripe_invoice_id=invoice_id)

    if not invoice:
        logger.warning(f'Invoice not found for user {user.id} with invoice ID: {invoice_id}')
        return

    invoice.payment_status = PaymentStatus.ACTION_REQUIRED
    await invoice.save()

    # You might want to notify the user about the required action
    # payment_intent = invoice.get("payment_intent")
    # if payment_intent:
    #     payment_intent_obj = stripe.PaymentIntent.retrieve(payment_intent)
    #     action_url = payment_intent_obj.get("next_action", {}).get("redirect_to_url", {}).get("url")
    #     if action_url:
    #         await send_payment_action_required_notification(user.email, db_invoice, action_url)
