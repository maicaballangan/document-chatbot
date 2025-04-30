from datetime import datetime
from http import HTTPStatus

import pytz
import stripe
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate

from app.core.authentication import NormalUser
from app.core.authentication import SuperUser
from app.core.enums import BillingCycle
from app.core.responses import badRequestResponse
from app.core.responses import conflictResponse
from app.core.responses import notFoundResponse
from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription_price import SubscriptionPrice
from app.models.subscription_price import SubscriptionPriceCreate
from app.models.subscription_price import SubscriptionPriceOutput
from app.models.subscription_price import SubscriptionPriceUpdate

router = APIRouter()


@router.get(
    '',
    dependencies=[NormalUser],
    response_model=Page[SubscriptionPriceOutput],
    status_code=HTTPStatus.OK,
)
async def get_all_subscription_price(
    limit: int = 100,
    offset: int = 0,
):
    """
    Search all records
    """
    query = SubscriptionPrice.filter(is_deleted=False).limit(limit).offset(offset)
    return await paginate(query)


@router.get(
    '/{id}',
    dependencies=[NormalUser],
    response_model=SubscriptionPriceOutput,
    status_code=HTTPStatus.OK,
    responses={**notFoundResponse},
)
async def get_subscription_price(
    id: int,
):
    """
    Get record by id
    """
    return await SubscriptionPrice.get(id=id, is_deleted=False)


@router.post(
    '',
    dependencies=[SuperUser],
    response_model=SubscriptionPriceOutput,
    status_code=HTTPStatus.CREATED,
    responses={**conflictResponse, **badRequestResponse},
)
async def create_subscription_price(input: SubscriptionPriceCreate):
    """
    Create new record (SuperUser)
    """
    plan = await SubscriptionPlan.get(id=input.subscription_plan_id)
    active_plan = await SubscriptionPrice.get_or_none(
        subscription_plan_id=input.subscription_plan_id, billing_cycle=input.billing_cycle
    )
    if active_plan is not None:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Subscription plan for specified billing_cycle already exists',
        )
    stripe_price = stripe.Price.create(
        product=plan.stripe_product_id,
        unit_amount_decimal=input.amount * 100,  # unit_amount_decimal in cents
        currency=input.currency,
        billing_scheme='per_unit',
        recurring={
            'interval': 'month' if input.billing_cycle is BillingCycle.MONTHLY else 'year',
            'interval_count': 1,
            'trial_period_days': plan.trial_period,
        },
    )
    return await SubscriptionPrice.create(stripe_price_id=stripe_price.id, **input.model_dump())


@router.put(
    '/{id}',
    dependencies=[SuperUser],
    response_model=SubscriptionPriceOutput,
    status_code=HTTPStatus.OK,
    responses={**notFoundResponse, **badRequestResponse},
)
async def update_subscription_price(id: int, input: SubscriptionPriceUpdate):
    """
    Update record (SuperUser)
    """
    record = await SubscriptionPrice.get(id=id, is_deleted=False).prefetch_related('subscription_plan')
    stripe.Price.modify(id=record.stripe_price_id, active=False)

    new_stripe_price = stripe.Price.create(
        product=record.subscription_plan.stripe_product_id,
        unit_amount_decimal=input.amount * 100,  # unit_amount_decimal in cents
        currency=record.currency.value,
        billing_scheme='per_unit',
        recurring={
            'interval': 'month' if record.billing_cycle is BillingCycle.MONTHLY else 'year',
            'interval_count': 1,
        },
    )
    record.stripe_price_id = new_stripe_price.id
    record.amount = input.amount
    await record.save()
    return record


@router.delete(
    '/{id}',
    dependencies=[SuperUser],
    status_code=HTTPStatus.NO_CONTENT,
    responses={**notFoundResponse, **badRequestResponse},
)
async def delete_subscription_price(id: int):
    """
    Delete record (SuperUser)
    """
    record = await SubscriptionPrice.get(id=id, is_deleted=False)
    stripe.Price.modify(id=record.stripe_price_id, active=False)

    record.is_deleted = True
    record.deleted_at = datetime.now(tz=pytz.utc)
    await record.save()
