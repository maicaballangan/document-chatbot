from http import HTTPStatus
from unittest import mock

import stripe
from httpx import AsyncClient

from app.core.config import settings
from app.models.subscription_price import SubscriptionPrice
from tests.utils.utils import random_integer
from tests.utils.utils import subscription_price_mock

BASE_URL = f'{settings.API_V1_STR}/subscription_prices'


async def test_get_all_subscriptionprice(client: AsyncClient, subscription_plan_mock, normaluser_token_headers) -> None:
    rec1 = await subscription_price_mock(subscription_plan_mock.id)
    rec2 = await subscription_price_mock(subscription_plan_mock.id)
    rec3 = await subscription_price_mock(subscription_plan_mock.id)

    r = await client.get(BASE_URL, headers=normaluser_token_headers)
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
        assert 'subscription_plan_id' in item
        assert 'billing_cycle' in item
        assert 'amount' in item
        assert 'currency' in item

    await rec1.delete()
    await rec2.delete()
    await rec3.delete()


async def test_get_subscriptionprice(client: AsyncClient, subscription_price_mock, normaluser_token_headers) -> None:
    r = await client.get(
        f'{BASE_URL}/{subscription_price_mock.id}',
        headers=normaluser_token_headers,
    )
    result = r.json()

    assert r.status_code == HTTPStatus.OK
    assert result['id'] == subscription_price_mock.id
    assert 'subscription_plan_id' in result
    assert 'billing_cycle' in result
    assert 'amount' in result
    assert 'currency' in result


async def test_get_subscriptionprice_nonexisting(client: AsyncClient, normaluser_token_headers) -> None:
    r = await client.get(
        f'{BASE_URL}/{random_integer()}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_create_subscriptionprice(client: AsyncClient, subscription_plan_mock, superuser_token_headers) -> None:
    with mock.patch('stripe.Price.create') as mock_create:
        # Create a real stripe.Price instance instead of a custom object
        mock_response = stripe.Price(
            id='price_mock_1235',
            object='price',
            active=True,
            billing_scheme='per_unit',
            created=1609459200,  # Jan 1, 2021
            currency='usd',
            livemode=False,
            metadata={},
            product='prod_xxxx',
            recurring={
                'interval': 'month',
                'interval_count': 1,
                'usage_type': 'licensed',
            },
            tax_behavior='exclusive',
            type='recurring',
            unit_amount=10000,  # $100.00 in cents
            unit_amount_decimal='10000',
        )
        mock_create.return_value = mock_response

        data = {
            'subscription_plan_id': subscription_plan_mock.id,
            'billing_cycle': 'monthly',
            'amount': 100.00,
            'currency': 'USD',
        }
        r = await client.post(
            BASE_URL,
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == HTTPStatus.CREATED

        record = await SubscriptionPrice.get_or_none(id=r.json()['id'], stripe_price_id=mock_response['id'])
        assert record is not None
        assert r.json()['subscription_plan_id'] == data['subscription_plan_id']
        assert r.json()['billing_cycle'] == data['billing_cycle']
        assert r.json()['amount'] == data['amount']
        assert r.json()['currency'] == data['currency']

        await record.delete()


async def test_create_subscriptionprice_conflict(
    client: AsyncClient, subscription_price_mock, superuser_token_headers
) -> None:
    data = {
        'subscription_plan_id': subscription_price_mock.subscription_plan_id,
        'billing_cycle': subscription_price_mock.billing_cycle,
        'amount': 100.00,
        'currency': 'USD',
    }
    r = await client.post(
        BASE_URL,
        headers=superuser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.CONFLICT


async def test_create_subscriptionprice_forbidden(
    client: AsyncClient, subscription_plan_mock, normaluser_token_headers
) -> None:
    data = {
        'subscription_plan_id': subscription_plan_mock.id,
        'billing_cycle': 'monthly',
        'amount': 100.00,
        'currency': 'USD',
    }
    r = await client.post(
        BASE_URL,
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.FORBIDDEN
    assert await SubscriptionPrice.exists(subscription_plan_id=data['subscription_plan_id']) is False


async def test_create_subscriptionprice_stripe_error(
    client: AsyncClient, subscription_plan_mock, superuser_token_headers
) -> None:
    with mock.patch('stripe.Price.create', side_effect=stripe.StripeError('Stripe API Error')):
        data = {
            'subscription_plan_id': subscription_plan_mock.id,
            'billing_cycle': 'monthly',
            'amount': 100.00,
            'currency': 'USD',
        }
        r = await client.post(
            BASE_URL,
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == HTTPStatus.BAD_REQUEST
        assert await SubscriptionPrice.exists(subscription_plan_id=data['subscription_plan_id']) is False


async def test_update_subscriptionprice_forbidden(
    client: AsyncClient, subscription_price_mock, normaluser_token_headers
) -> None:
    data = {
        'amount': 99.99,
    }
    r = await client.put(
        f'{BASE_URL}/{subscription_price_mock.id}',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.FORBIDDEN
    assert await SubscriptionPrice.exists(amount=data['amount']) is False


async def test_update_subscriptionprice_stripe_error(
    client: AsyncClient, subscription_price_mock, superuser_token_headers
) -> None:
    with (
        mock.patch('stripe.Price.modify', side_effect=stripe.StripeError('Stripe API Error')),
        mock.patch('stripe.Price.create', side_effect=stripe.StripeError('Stripe API Error')),
    ):
        data = {
            'amount': 99.99,
        }
        r = await client.put(
            f'{BASE_URL}/{subscription_price_mock.id}',
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == HTTPStatus.BAD_REQUEST
        assert await SubscriptionPrice.exists(amount=data['amount']) is False


async def test_update_subscriptionprice(client: AsyncClient, subscription_price_mock, superuser_token_headers) -> None:
    with mock.patch('stripe.Price.modify'), mock.patch('stripe.Price.create') as mock_create:
        # Create a structured mock price object for this test
        price_data = {
            'id': f'price_{random_integer()}',
            'object': 'price',
            'active': True,
            'billing_scheme': 'per_unit',
            'created': 1609459200,  # Jan 1, 2021
            'currency': 'usd',
            'livemode': False,
            'metadata': {},
            'product': 'prod_xxxx',
            'recurring': {
                'interval': 'month',
                'interval_count': 1,
            },
            'unit_amount': 9999,  # $99.99 in cents
            'unit_amount_decimal': '9999',
        }

        price_obj = type('StripePriceObject', (), price_data)
        mock_create.return_value = price_obj

        data = {
            'amount': 99.99,
        }
        r = await client.put(
            f'{BASE_URL}/{subscription_price_mock.id}',
            headers=superuser_token_headers,
            json=data,
        )
        assert r.status_code == HTTPStatus.OK
        assert r.json()['amount'] == data['amount']
        assert await SubscriptionPrice.exists(amount=data['amount'], stripe_price_id=price_data['id']) is True


async def test_delete_subscriptionprice(client: AsyncClient, subscription_price_mock, superuser_token_headers) -> None:
    with mock.patch('stripe.Price.modify') as mock_modify:
        # Create a real stripe.Price instance instead of a custom object
        mock_response = stripe.Price(id='price_mock_111', object='price', active=False, metadata={'deleted': 'true'})
        mock_modify.return_value = mock_response

        r = await client.delete(
            f'{BASE_URL}/{subscription_price_mock.id}',
            headers=superuser_token_headers,
        )
        assert r.status_code == HTTPStatus.NO_CONTENT
        price = await SubscriptionPrice.get_or_none(id=subscription_price_mock.id)
        assert price is not None
        assert price.deleted_at is not None

        r = await client.get(
            f'{BASE_URL}/{subscription_price_mock.id}',
            headers=superuser_token_headers,
        )
        assert r.status_code == HTTPStatus.NOT_FOUND


async def test_delete_subscriptionprice_nonexisting(client: AsyncClient, superuser_token_headers) -> None:
    r = await client.delete(
        f'{BASE_URL}/{random_integer()}',
        headers=superuser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_delete_subscriptionprice_forbidden(
    client: AsyncClient, subscription_price_mock, normaluser_token_headers
) -> None:
    r = await client.delete(
        f'{BASE_URL}/{subscription_price_mock.id}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.FORBIDDEN


async def test_delete_subscriptionprice_stripe_error(
    client: AsyncClient, subscription_price_mock, superuser_token_headers
) -> None:
    with mock.patch('stripe.Price.modify', side_effect=stripe.StripeError('Stripe API Error')):
        r = await client.delete(
            f'{BASE_URL}/{subscription_price_mock.id}',
            headers=superuser_token_headers,
        )
        assert r.status_code == HTTPStatus.BAD_REQUEST

        price = await SubscriptionPrice.get_or_none(id=subscription_price_mock.id)  # soft delete
        assert price is not None
        assert price.deleted_at is None
