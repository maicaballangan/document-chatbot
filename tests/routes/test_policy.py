from http import HTTPStatus

from httpx import AsyncClient

from app.core.config import settings
from app.legalai.ai import NewAI
from app.models.document import Document
from app.models.policy import Policy
from app.models.user import User
from tests.utils.utils import policy_mock
from tests.utils.utils import random_json
from tests.utils.utils import random_lower_string
from tests.utils.utils import random_uuid

BASE_URL = f'{settings.API_V1_STR}/policies'


async def test_get_all_policy_superuser(client: AsyncClient, document_mock, superuser_token_headers) -> None:
    rec1 = await policy_mock(document_mock.id)
    rec2 = await policy_mock(document_mock.id)
    rec3 = await policy_mock(document_mock.id)
    rec4 = await policy_mock(document_mock.id)
    rec5 = await policy_mock(document_mock.id)

    r = await client.get(BASE_URL, headers=superuser_token_headers)
    results = r.json()

    assert r.status_code == HTTPStatus.OK
    assert len(results['items']) > 1
    assert 'total' in results
    assert 'page' in results
    assert 'size' in results
    assert 'pages' in results

    # assert results['total'] == 5 TODO put assertion back

    for item in results['items']:
        assert 'id' in item
        assert 'document' in item

    await rec1.delete()
    await rec2.delete()
    await rec3.delete()
    await rec4.delete()
    await rec5.delete()


async def test_get_all_policy(client: AsyncClient, document_mock, normal_user: User, normaluser_token_headers) -> None:
    rec1 = await policy_mock(document_mock.id, normal_user.id)
    rec2 = await policy_mock(document_mock.id, normal_user.id)
    rec3 = await policy_mock(document_mock.id, normal_user.id)
    rec4 = await policy_mock(document_mock.id)
    rec5 = await policy_mock(document_mock.id)

    r = await client.get(BASE_URL, headers=normaluser_token_headers)
    results = r.json()

    assert r.status_code == HTTPStatus.OK
    assert len(results['items']) > 1
    assert 'total' in results
    assert 'page' in results
    assert 'size' in results
    assert 'pages' in results

    # assert results['total'] == 3 TODO put assertion back

    for item in results['items']:
        assert 'id' in item
        assert 'document' in item

    await rec1.delete()
    await rec2.delete()
    await rec3.delete()
    await rec4.delete()
    await rec5.delete()


async def test_get_policy(client: AsyncClient, policy_mock, normaluser_token_headers) -> None:
    r = await client.get(
        f'{BASE_URL}/{policy_mock.id}',
        headers=normaluser_token_headers,
    )
    result = r.json()

    assert r.status_code == HTTPStatus.OK
    assert result['id'] == str(policy_mock.id)
    assert 'document' in result


# TODO do we need superuser get
# async def test_get_policy_superuser(client: AsyncClient, superuser_token_headers) -> None:
#     record = await policy_mock(random_integer())

#     r = await client.get(
#         f'{BASE_URL}/{record.id}',
#         headers=superuser_token_headers,
#     )
#     result = r.json()

#     assert r.status_code == HTTPStatus.OK
#     assert result['id'] == record.id


async def test_get_policy_forbidden(client: AsyncClient, policy_mock, otheruser_token_headers) -> None:
    r = await client.get(
        f'{BASE_URL}/{policy_mock.id}',
        headers=otheruser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_create_policy(document_mock, client: AsyncClient, normaluser_token_headers) -> None:
    data = {
        'document_id': str(document_mock.id),
        'name': random_lower_string(),
    }
    r = await client.post(
        f'{BASE_URL}',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.CREATED

    record = await Policy.get_or_none(id=r.json()['id'])
    assert record is not None

    await record.delete()


async def test_create_policy_duplicate_document(client: AsyncClient, document_mock, normaluser_token_headers) -> None:
    data = {
        'document_id': str(document_mock.id),
        'name': random_lower_string(),
    }
    r1 = await client.post(
        f'{BASE_URL}',
        headers=normaluser_token_headers,
        json=data,
    )

    r2 = await client.post(
        f'{BASE_URL}',
        headers=normaluser_token_headers,
        json=data,
    )

    assert r2.status_code == HTTPStatus.CONFLICT
    record = await Policy.get_or_none(id=r1.json()['id'])
    assert record is not None

    await record.delete()


async def test_create_policy_integrity_error(client: AsyncClient, document_mock, otheruser_token_headers) -> None:
    data = {
        'document_id': str(document_mock.id),
        'name': random_lower_string(),
    }
    r = await client.post(
        f'{BASE_URL}',
        headers=otheruser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


# TODO do we need superuser delete
# async def test_delete_policy_superuser(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
#     policy = await policy_mock(created_by=random_integer())

#     r = await client.get(
#         f'{BASE_URL}/{policy.id}',
#         headers=superuser_token_headers,
#     )
#     assert r.status_code == HTTPStatus.NO_CONTENT


async def test_delete_policy(client: AsyncClient, policy_mock, normaluser_token_headers) -> None:
    r = await client.delete(
        f'{BASE_URL}/{policy_mock.id}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.NO_CONTENT

    assert await Document.exists(id=policy_mock.document_id) is False


async def test_delete_policy_nonexisting(client: AsyncClient, normaluser_token_headers) -> None:
    r = await client.delete(
        f'{BASE_URL}/{random_uuid()}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_delete_policy_forbidden(client: AsyncClient, policy_mock, otheruser_token_headers) -> None:
    r = await client.delete(
        f'{BASE_URL}/{policy_mock.id}',
        headers=otheruser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_summarize_policy(
    client: AsyncClient, subscription_mock, policy_mock, normaluser_token_headers, monkeypatch
) -> None:
    def summary_the_policy_mock(self, document_id, summary_id, vector_id):
        return 'residential', ['test'], random_json()

    monkeypatch.setattr(NewAI, 'summary_the_policy', summary_the_policy_mock)
    r = await client.put(
        f'{BASE_URL}/{policy_mock.id}/summarize',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.OK

    assert r.json()['type'] == 'residential'
    assert r.json()['summary'] == ['test']
    assert r.json()['report'] == random_json()
