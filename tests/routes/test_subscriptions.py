from datetime import datetime
from http import HTTPStatus
from unittest import mock

import stripe
from httpx import AsyncClient

from app.core.config import settings
from app.core.enums import SubscriptionStatus
from app.models.subscription import Subscription
from tests.utils.utils import random_integer
from tests.utils.utils import random_url
from tests.utils.utils import subscription_mock

BASE_URL = f'{settings.API_V1_STR}/subscriptions'


async def test_get_all_subscription(
    client: AsyncClient, subscription_price_mock, normal_user, superuser_token_headers
) -> None:
    rec1 = await subscription_mock(subscription_price_mock.id, normal_user.id)
    rec2 = await subscription_mock(subscription_price_mock.id, normal_user.id)
    rec3 = await subscription_mock(subscription_price_mock.id, normal_user.id)

    r = await client.get(BASE_URL, headers=superuser_token_headers)
    results = r.json()

    assert r.status_code == HTTPStatus.OK
    assert len(results['items']) == 3
    assert 'total' in results
    assert 'page' in results
    assert 'size' in results
    assert 'pages' in results

    assert results['total'] == 3

    for item in results['items']:
        assert 'id' in item
        assert 'user_id' in item
        assert 'subscription_price_id' in item
        assert 'status' in item
        assert 'current_period_end' in item
        assert 'trial_period_end' in item
        assert 'expired_at' in item
        assert 'stripe_subscription_id' in item

    await rec1.delete()
    await rec2.delete()
    await rec3.delete()


async def test_get_subscription(client: AsyncClient, subscription_mock, superuser_token_headers) -> None:
    r = await client.get(
        f'{BASE_URL}/{subscription_mock.id}',
        headers=superuser_token_headers,
    )
    result = r.json()

    assert r.status_code == HTTPStatus.OK
    assert result['id'] == subscription_mock.id
    assert 'user_id' in result
    assert 'subscription_price_id' in result
    assert 'status' in result
    assert 'current_period_end' in result
    assert 'trial_period_end' in result
    assert 'expired_at' in result
    assert 'stripe_subscription_id' in result


async def test_get_subscription_forbidden(client: AsyncClient, subscription_mock, normaluser_token_headers) -> None:
    r = await client.get(
        f'{BASE_URL}/{subscription_mock.id}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.FORBIDDEN


async def test_create_subscription(
    client: AsyncClient, subscription_price_mock, normal_user, normaluser_token_headers
) -> None:
    success_url = random_url()
    cancel_url = random_url()
    checkout_url = random_url()

    # Create a proper mock for stripe.checkout.Session.create
    mock_session = mock.MagicMock()
    mock_session.id = 'stripe_session_id_mock'
    mock_session.url = checkout_url

    with (
        mock.patch('stripe.checkout.Session.create', return_value=mock_session),
        mock.patch('app.routes.subscriptions.get_or_create_stripe_customer', return_value='mock_customer_id'),
    ):
        data = {
            'subscription_price_id': subscription_price_mock.id,
            'success_url': success_url,
            'cancel_url': cancel_url,
        }

        r = await client.post(
            BASE_URL,
            headers=normaluser_token_headers,
            json=data,
        )

        assert r.status_code == HTTPStatus.CREATED
        result = r.json()
        assert result['session_id'] == 'stripe_session_id_mock'
        assert result['url'] == checkout_url


async def test_create_subscription_conflict(
    client: AsyncClient, subscription_mock, subscription_price_mock, normal_user, normaluser_token_headers
) -> None:
    # Ensure the subscription belongs to the normal_user
    subscription_mock.user_id = normal_user.id
    subscription_mock.subscription_price_id = subscription_price_mock.id
    subscription_mock.status = SubscriptionStatus.ACTIVE
    await subscription_mock.save()

    data = {
        'subscription_price_id': subscription_price_mock.id,
        'success_url': random_url(),
        'cancel_url': random_url(),
    }

    # Mock the get_or_create_stripe_customer function
    with mock.patch('app.routes.subscriptions.get_or_create_stripe_customer', return_value='mock_customer_id'):
        r = await client.post(
            BASE_URL,
            headers=normaluser_token_headers,
            json=data,
        )
        assert r.status_code == HTTPStatus.CONFLICT


async def test_get_current_subscription(
    client: AsyncClient, subscription_price_mock, normal_user, normaluser_token_headers
) -> None:
    # Create a subscription for the normal user
    subscription = await subscription_mock(subscription_price_mock.id, normal_user.id)
    subscription.status = SubscriptionStatus.ACTIVE
    await subscription.save()

    r = await client.get(
        f'{BASE_URL}/current',
        headers=normaluser_token_headers,
    )

    assert r.status_code == HTTPStatus.OK
    result = r.json()
    assert result['id'] == subscription.id
    assert result['user_id'] == normal_user.id

    await subscription.delete()


async def test_cancel_current_subscription(
    client: AsyncClient, subscription_price_mock, normal_user, normaluser_token_headers
) -> None:
    # Create a subscription for the normal user
    subscription = await subscription_mock(subscription_price_mock.id, normal_user.id)
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.stripe_subscription_id = 'mock_stripe_subscription_id'
    await subscription.save()

    # Mock Stripe API calls
    timestamp = int(datetime.now().timestamp())
    mock_stripe_subscription = {'current_period_start': timestamp, 'canceled_at': timestamp}

    with (
        mock.patch('stripe.Subscription.modify') as mock_modify,
        mock.patch('stripe.Subscription.retrieve', return_value=mock_stripe_subscription) as mock_retrieve,
    ):
        r = await client.delete(
            f'{BASE_URL}/current',
            headers=normaluser_token_headers,
        )

        assert r.status_code == HTTPStatus.NO_CONTENT

        # Verify the Stripe API was called correctly
        mock_modify.assert_called_once_with(subscription.stripe_subscription_id, cancel_at_period_end=True)
        mock_retrieve.assert_called_once_with(subscription.stripe_subscription_id)

        # Verify the subscription was updated
        updated_subscription = await Subscription.get(id=subscription.id)
        assert updated_subscription.canceled_at is not None

        await subscription.delete()


async def test_cancel_subscription_immediately(client: AsyncClient, subscription_mock, superuser_token_headers) -> None:
    subscription_mock.stripe_subscription_id = 'mock_stripe_subscription_id'
    await subscription_mock.save()

    # Mock Stripe API calls
    timestamp = int(datetime.now().timestamp())
    mock_stripe_subscription = {'current_period_start': timestamp, 'canceled_at': timestamp}

    with (
        mock.patch('stripe.Subscription.cancel') as mock_cancel,
        mock.patch('stripe.Subscription.retrieve', return_value=mock_stripe_subscription) as mock_retrieve,
    ):
        r = await client.delete(
            f'{BASE_URL}/{subscription_mock.id}',
            headers=superuser_token_headers,
        )

        assert r.status_code == HTTPStatus.NO_CONTENT

        # Verify the Stripe API was called correctly
        mock_cancel.assert_called_once_with(subscription_mock.stripe_subscription_id)
        mock_retrieve.assert_called_once_with(subscription_mock.stripe_subscription_id)

        # Verify the subscription was updated
        updated_subscription = await Subscription.get(id=subscription_mock.id)
        assert updated_subscription.canceled_at is not None
        assert updated_subscription.status == SubscriptionStatus.CANCELED


async def test_delete_subscription_nonexisting(client: AsyncClient, superuser_token_headers) -> None:
    r = await client.delete(
        f'{BASE_URL}/{random_integer()}',
        headers=superuser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_delete_subscription_forbidden(client: AsyncClient, subscription_mock, normaluser_token_headers) -> None:
    r = await client.delete(
        f'{BASE_URL}/{subscription_mock.id}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.FORBIDDEN


async def test_delete_subscription_stripe_error(
    client: AsyncClient, subscription_mock, superuser_token_headers
) -> None:
    with mock.patch('stripe.Subscription.cancel', side_effect=stripe.StripeError):
        r = await client.delete(
            f'{BASE_URL}/{subscription_mock.id}',
            headers=superuser_token_headers,
        )
        assert r.status_code == HTTPStatus.BAD_REQUEST
        assert await Subscription.exists(id=subscription_mock.id) is True
