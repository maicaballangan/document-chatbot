from http import HTTPStatus

import stripe
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate

from app.core.authentication import NormalUser
from app.core.authentication import SuperUser
from app.core.responses import badRequestResponse
from app.core.responses import conflictResponse
from app.core.responses import notFoundResponse
from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription_plan import SubscriptionPlanCreate
from app.models.subscription_plan import SubscriptionPlanOutput
from app.models.subscription_plan import SubscriptionPlanUpdate
from app.models.subscription_price import SubscriptionPrice

router = APIRouter()


@router.get(
    '',
    dependencies=[NormalUser],
    response_model=Page[SubscriptionPlanOutput],
    status_code=HTTPStatus.OK,
)
async def get_all_subscription_plan(
    limit: int = 100,
    offset: int = 0,
):
    """
    Search all records records
    """
    query = SubscriptionPlan.all().limit(limit).offset(offset)
    return await paginate(query)


@router.get(
    '/{id}',
    dependencies=[NormalUser],
    response_model=SubscriptionPlanOutput,
    status_code=HTTPStatus.OK,
    responses={**notFoundResponse},
)
async def get_subscription_plan(
    id: int,
):
    """
    Get record by id
    """
    return await SubscriptionPlan.get(id=id)


@router.post(
    '',
    dependencies=[SuperUser],
    response_model=SubscriptionPlanOutput,
    status_code=HTTPStatus.CREATED,
    responses={**badRequestResponse},
)
async def create_subscription_plan(input: SubscriptionPlanCreate):
    """
    Create new record (SuperUser)
    """
    stripe_product = stripe.Product.create(
        name=input.name,
    )
    return await SubscriptionPlan.create(stripe_product_id=stripe_product.id, **input.model_dump())


@router.put(
    '/{id}',
    dependencies=[SuperUser],
    response_model=SubscriptionPlanOutput,
    status_code=HTTPStatus.OK,
    responses={**notFoundResponse, **badRequestResponse},
)
async def update_subscription_plan(id: int, input: SubscriptionPlanUpdate):
    """
    Update record (SuperUser)
    """
    record = await SubscriptionPlan.get(id=id)
    stripe.Product.modify(id=record.stripe_product_id, name=input.name)

    await record.update_from_dict(input.model_dump()).save()
    return record


@router.delete(
    '/{id}',
    dependencies=[SuperUser],
    status_code=HTTPStatus.NO_CONTENT,
    responses={**notFoundResponse, **conflictResponse, **badRequestResponse},
)
async def delete_subscription_plan(id: int):
    """
    Delete a record (SuperUser)
    """
    record = await SubscriptionPlan.get(id=id)
    price = await SubscriptionPrice.get_or_none(subscription_plan_id=record.id, is_deleted=False)
    if price is not None:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Unable to delete subscription plan with active subscription pricings',
        )
    stripe.Product.delete(sid=record.stripe_product_id)
    await record.delete()
