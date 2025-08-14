from http import HTTPStatus

import pytest
from fastapi import HTTPException

from app.core.authentication import check_privileges
from app.core.enums import SubscriptionStatus
from app.models.user import User


async def test_check_privileges_with_valid_privilege(normal_user: User, subscription_mock, subscription_plan_mock):
    subscription_plan_mock.chat_with_files = True
    await subscription_plan_mock.save()

    result = await check_privileges(normal_user, privilege='chat_with_files')
    assert result == normal_user


async def test_check_privileges_admin(super_user: User):
    result = await check_privileges(super_user, privilege='chat_with_files')
    assert result == super_user


async def test_check_privileges_with_invalid_privilege(normal_user: User, subscription_mock, subscription_plan_mock):
    subscription_plan_mock.chat_with_files = False
    await subscription_plan_mock.save()

    with pytest.raises(HTTPException) as exc_info:
        await check_privileges(normal_user, privilege='chat_with_files')
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
    assert exc_info.value.detail == 'Access denied. Required privilege: chat_with_files.'


async def test_check_privileges_no_active_subscription(normal_user: User, subscription_mock):
    subscription_mock.status = SubscriptionStatus.CANCELED
    await subscription_mock.save()

    with pytest.raises(HTTPException) as exc_info:
        await check_privileges(normal_user, privilege='chat_with_files')
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
    assert exc_info.value.detail == 'No active subscription found.'


async def test_check_privileges_no_subscription_plan(normal_user: User, subscription_mock):
    subscription_mock.subscription_price_id = None
    await subscription_mock.save()
    with pytest.raises(HTTPException) as exc_info:
        await check_privileges(normal_user, privilege='chat_with_files')
    assert exc_info.value.status_code == HTTPStatus.FORBIDDEN
    assert exc_info.value.detail == 'Subscription plan not found.'
