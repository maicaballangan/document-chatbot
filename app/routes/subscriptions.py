import logging
from datetime import datetime
from http import HTTPStatus

import stripe
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate

from app.core.authentication import CurrentUser
from app.core.authentication import SuperUser
from app.core.enums import SubscriptionStatus
from app.models.base import Checkout
from app.models.subscription import Subscription
from app.models.subscription import SubscriptionInput
from app.models.subscription import SubscriptionOutput
from app.models.subscription_price import SubscriptionPrice
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    '/current',
    response_model=SubscriptionOutput,
    status_code=HTTPStatus.OK,
)
async def get_current_subscription(current_user: CurrentUser):
    """
    Get currents active subscription
    """
    return await Subscription.get(
        user_id=current_user.id, status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]
    )


@router.delete(
    '/current',
    status_code=HTTPStatus.NO_CONTENT,
)
async def cancel_current_subscription(current_user: CurrentUser):
    """
    Delete current subscription
    """
    subscription = await Subscription.get(
        user_id=current_user.id,
        status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL, SubscriptionStatus.PAST_DUE],
    )

    stripe.Subscription.modify(subscription.stripe_subscription_id, cancel_at_period_end=True)
    stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)

    subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.get('current_period_start', 0))
    # TODO create daily cron to check for subscriptions with canceled_at that is not yet set to status = CANCELED at canceled_at EOD
    subscription.canceled_at = datetime.fromtimestamp(stripe_subscription.get('canceled_at', 0))
    await subscription.save()


@router.get(
    '',
    dependencies=[SuperUser],
    response_model=Page[SubscriptionOutput],
    status_code=HTTPStatus.OK,
)
async def get_all_subscription(
    limit: int = 100,
    offset: int = 0,
):
    """
    Search all records records (SuperUser)
    """
    query = Subscription.all().limit(limit).offset(offset)
    return await paginate(query)


@router.get(
    '/{id}',
    dependencies=[SuperUser],
    response_model=SubscriptionOutput,
    status_code=HTTPStatus.OK,
)
async def get_subscription(
    id: int,
):
    """
    Get record by id (SuperUser)
    """
    return await Subscription.get(id=id)


@router.post(
    '',
    response_model=Checkout,
    status_code=HTTPStatus.CREATED,
)
async def create_subscription(current_user: CurrentUser, input: SubscriptionInput):
    """
    Stripe payment session checkout
    """
    await get_or_create_stripe_customer(current_user)

    price = await SubscriptionPrice.get(id=input.subscription_price_id).prefetch_related('subscription_plan')
    active_subscription = await Subscription.get_or_none(
        user_id=current_user.id,
        subscription_price_id=price.id,
        status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL, SubscriptionStatus.PAST_DUE],
    )

    if active_subscription:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=f"A subscription for this plan already exists with status: {active_subscription.status}. Please ensure you don't double subscribe or cancel the existing subscription.",
        )

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        customer=current_user.stripe_customer_id,
        line_items=[{'price': price.stripe_price_id, 'quantity': 1}],
        mode='subscription',
        subscription_data={'trial_period_days': price.subscription_plan.trial_period}
        if price.subscription_plan.trial_period > 0
        else None,
        success_url=input.success_url,
        cancel_url=input.cancel_url,
        metadata={'user_id': current_user.id, 'type': 'subscription', 'subscription_price': price.id},
    )

    return Checkout(session_id=checkout_session.id, url=checkout_session.url)


async def get_or_create_stripe_customer(current_user: CurrentUser):
    """Get existing Stripe customer ID or create a new customer."""
    # Find the user
    user = await User.get(id=current_user.id)

    # If user already has a Stripe customer ID, return it
    if user.stripe_customer_id:
        return user.stripe_customer_id

    # Create a new Stripe customer
    customer = stripe.Customer.create(email=current_user.email, metadata={'user_id': str(current_user.id)})

    # Update user with new Stripe customer ID
    user.stripe_customer_id = customer.id
    await user.save()


@router.delete(
    '/{id}',
    dependencies=[SuperUser],
    status_code=HTTPStatus.NO_CONTENT,
)
async def cancel_subscription_immediately(id: int):
    """
    Cancel subscription immediately (SuperUser)
    """
    subscription = await Subscription.get(id=id)

    stripe.Subscription.cancel(subscription.stripe_subscription_id)
    stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
    subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.get('current_period_start', 0))
    subscription.status = SubscriptionStatus.CANCELED
    subscription.canceled_at = datetime.fromtimestamp(stripe_subscription.get('canceled_at', 0))
    await subscription.save()
