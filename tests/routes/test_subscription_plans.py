from http import HTTPStatus
from unittest import mock

import stripe
from httpx import AsyncClient

from app.core.config import settings
from app.models.subscription_plan import SubscriptionPlan
from tests.utils.utils import random_integer
from tests.utils.utils import random_lower_string
from tests.utils.utils import subscription_plan_mock

BASE_URL = f'{settings.API_V1_STR}/subscription_plans'


async def test_get_all_subscriptionplan(client: AsyncClient, normaluser_token_headers) -> None:
    rec1 = await subscription_plan_mock()
    rec2 = await subscription_plan_mock()
    rec3 = await subscription_plan_mock()

    r = await client.get(BASE_URL, headers=normaluser_token_headers)
    results = r.json()

    assert r.status_code == HTTPStatus.OK
    assert len(results['items']) == 3
    assert 'total' in results
    assert 'page' in results
    assert 'size' in results
    assert 'pages' in results

    # assert results['total'] == 3 TODO put assertion back

    for item in results['items']:
        assert 'id' in item
        assert 'chat_with_files' in item
        assert 'chat_with_folders' in item
        assert 'credits in item'
        assert 'customer_support_email' in item

    await rec1.delete()
    await rec2.delete()
    await rec3.delete()


async def test_get_subscriptionplan(client: AsyncClient, subscription_plan_mock, normaluser_token_headers) -> None:
    r = await client.get(
        f'{BASE_URL}/{subscription_plan_mock.id}',
        headers=normaluser_token_headers,
    )
    result = r.json()

    assert r.status_code == HTTPStatus.OK
    assert result['id'] == subscription_plan_mock.id
    assert 'name' in result


async def test_create_subscriptionplan(client: AsyncClient, superuser_token_headers) -> None:
    with mock.patch('stripe.Product.create') as mock_modify:
        mock_response = stripe.Product(id='prod_xxxx', object='product', name='Esquire')
        mock_modify.return_value = mock_response

        data = {
            'name': 'Esquire',
            'credits': random_integer(),
        }
        r = await client.post(
            BASE_URL,
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == HTTPStatus.CREATED

        record = await SubscriptionPlan.get_or_none(id=r.json()['id'], stripe_product_id='prod_xxxx')
        assert record is not None
        assert r.json()['name'] == data['name']
        await record.delete()


async def test_create_subscriptionplan_forbidden(client: AsyncClient, normaluser_token_headers) -> None:
    data = {
        'name': random_lower_string(),
    }
    r = await client.post(
        BASE_URL,
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.FORBIDDEN
    assert await SubscriptionPlan.exists(name=data['name']) is False


async def test_create_subscriptionplan_stripe_error(client: AsyncClient, superuser_token_headers) -> None:
    with mock.patch('stripe.Product.create', side_effect=stripe.StripeError('Stripe API Error')):
        data = {
            'name': random_lower_string(),
        }
        r = await client.post(
            BASE_URL,
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == HTTPStatus.BAD_REQUEST
        assert await SubscriptionPlan.exists(name=data['name']) is False


async def test_update_subscriptionplan(client: AsyncClient, subscription_plan_mock, superuser_token_headers) -> None:
    with mock.patch('stripe.Product.modify') as mock_modify:
        mock_response = stripe.Product(
            id=subscription_plan_mock.stripe_product_id, object='product', name='EsquireModified'
        )
        mock_modify.return_value = mock_response

        data = {
            'name': 'EsquireModified',
        }
        r = await client.put(
            f'{BASE_URL}/{subscription_plan_mock.id}',
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == HTTPStatus.OK
        assert r.json()['name'] == data['name']


async def test_update_subscriptionplan_forbidden(
    client: AsyncClient, subscription_plan_mock, normaluser_token_headers
) -> None:
    data = {
        'name': random_lower_string(),
    }
    r = await client.put(
        f'{BASE_URL}/{subscription_plan_mock.id}',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.FORBIDDEN
    assert await SubscriptionPlan.exists(name=data['name']) is False


async def test_update_subscriptionplan_stripe_error(
    client: AsyncClient, subscription_plan_mock, superuser_token_headers
) -> None:
    with mock.patch('stripe.Product.modify', side_effect=stripe.StripeError('Stripe API Error')):
        data = {
            'name': random_lower_string(),
        }
        r = await client.put(
            f'{BASE_URL}/{subscription_plan_mock.id}',
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == HTTPStatus.BAD_REQUEST
        assert await SubscriptionPlan.exists(name=data['name']) is False
        assert await SubscriptionPlan.exists(name=subscription_plan_mock.name) is True


async def test_delete_subscriptionplan(client: AsyncClient, subscription_plan_mock, superuser_token_headers) -> None:
    with mock.patch('stripe.Product.delete') as mock_delete:
        mock_response = stripe.Product(
            id=subscription_plan_mock.stripe_product_id, object='product', name='Esquire', deleted=True
        )
        mock_delete.return_value = mock_response

        r = await client.delete(
            f'{BASE_URL}/{subscription_plan_mock.id}',
            headers=superuser_token_headers,
        )
        assert r.status_code == HTTPStatus.NO_CONTENT
        assert await SubscriptionPlan.exists(id=subscription_plan_mock.id) is False


async def test_delete_subscriptionplan_nonexisting(client: AsyncClient, superuser_token_headers) -> None:
    r = await client.delete(
        f'{BASE_URL}/{random_integer()}',
        headers=superuser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_delete_subscriptionplan_forbidden(
    client: AsyncClient, subscription_plan_mock, normaluser_token_headers
) -> None:
    r = await client.delete(
        f'{BASE_URL}/{subscription_plan_mock.id}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.FORBIDDEN


async def test_delete_subscriptionplan_stripe_error(
    client: AsyncClient, subscription_plan_mock, superuser_token_headers
) -> None:
    with mock.patch('stripe.Product.delete', side_effect=stripe.StripeError('Stripe API Error')):
        r = await client.delete(
            f'{BASE_URL}/{subscription_plan_mock.id}',
            headers=superuser_token_headers,
        )
        assert r.status_code == HTTPStatus.BAD_REQUEST
        assert await SubscriptionPlan.exists(id=subscription_plan_mock.id) is True


async def test_delete_subscriptionplan_conflict(
    client: AsyncClient, subscription_price_mock, subscription_plan_mock, superuser_token_headers
) -> None:
    r = await client.delete(
        f'{BASE_URL}/{subscription_plan_mock.id}',
        headers=superuser_token_headers,
    )
    assert r.status_code == HTTPStatus.CONFLICT
    assert await SubscriptionPlan.exists(id=subscription_plan_mock.id) is True
    await subscription_price_mock.delete()
