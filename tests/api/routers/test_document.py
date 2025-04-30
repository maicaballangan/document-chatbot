from http import HTTPStatus

from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from app.core.config import settings
from app.core.enums import ExtractionStatus
from app.models.document import Document
from app.models.user import User
from app.utils.security import create_app_token
from tests.utils.utils import document_mock
from tests.utils.utils import random_float
from tests.utils.utils import random_integer
from tests.utils.utils import random_uuid
from tests.utils.utils import random_uuid_str

BASE_URL = f'{settings.API_V1_STR}/documents'


async def test_get_all_document(client: AsyncClient, normal_user: User, superuser_token_headers) -> None:
    doc1 = await document_mock(normal_user.id)
    doc2 = await document_mock(normal_user.id)
    doc3 = await document_mock(normal_user.id)
    doc4 = await document_mock(normal_user.id)
    doc5 = await document_mock(normal_user.id)

    r = await client.get(BASE_URL, headers=superuser_token_headers)
    results = r.json()

    assert r.status_code == HTTPStatus.OK
    assert len(results['items']) > 1
    assert 'total' in results
    assert 'page' in results
    assert 'size' in results
    assert 'pages' in results

    # assert results['total'] == 5 // TODO put this assertion back

    for item in results['items']:
        assert 'id' in item

    await doc1.delete()
    await doc2.delete()
    await doc3.delete()
    await doc4.delete()
    await doc5.delete()


async def test_get_document(client: AsyncClient, document_mock, normaluser_token_headers) -> None:
    r = await client.get(
        f'{BASE_URL}/{document_mock.id}',
        headers=normaluser_token_headers,
    )
    result = r.json()

    assert r.status_code == HTTPStatus.OK
    assert result['id'] == str(document_mock.id)


# TODO ask if we need superuser
# async def test_get_document_superuser(client: AsyncClient, superuser_token_headers) -> None:
#     document = await document_mock(random_integer())

#     r = await client.get(
#         f'{BASE_URL}/{document.id}',
#         headers=superuser_token_headers,
#     )
#     result = r.json()

#     assert r.status_code == HTTPStatus.OK
#     assert result['id'] == document.id


async def test_get_document_forbidden(client: AsyncClient, document_mock, otheruser_token_headers) -> None:
    r = await client.get(
        f'{BASE_URL}/{document_mock.id}',
        headers=otheruser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_update_document(client: AsyncClient, document_mock, media_processor_token_headers) -> None:
    data = {
        'summary_id': random_uuid_str(),
        'vector_id': random_uuid_str(),
        'extract_duration': random_float(),
        'total_pages': random_integer(),
        'status': 'success',
        'content': ['this', 'is', '4', 'pages'],
    }

    r = await client.put(
        f'{BASE_URL}/{document_mock.id}',
        headers=media_processor_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.OK
    assert r.json()['vector_id'] == data['vector_id']
    assert r.json()['summary_id'] == data['summary_id']
    assert r.json()['extract_duration'] == data['extract_duration']
    assert r.json()['total_pages'] == data['total_pages']
    assert r.json()['status'] == data['status']
    assert r.json()['content'] == data['content']
    assert r.json()['total_pages'] == data['total_pages']

    updated = await Document.get(id=document_mock.id)
    assert updated.vector_id == data['vector_id']
    assert updated.summary_id == data['summary_id']
    assert updated.extract_duration == data['extract_duration']
    assert updated.total_pages == data['total_pages']
    assert updated.status == data['status']
    assert updated.content == data['content']
    assert updated.total_pages == data['total_pages']


async def test_update_document_superuser_unauthorized(
    client: AsyncClient, document_mock, superuser_token_headers
) -> None:
    r = await client.put(
        f'{BASE_URL}/{document_mock.id}',
        headers=superuser_token_headers,
    )
    assert r.status_code == HTTPStatus.UNAUTHORIZED


async def test_update_document_unauthorized(client: AsyncClient, document_mock, otheruser_token_headers) -> None:
    r = await client.put(
        f'{BASE_URL}/{document_mock.id}',
        headers=otheruser_token_headers,
    )
    assert r.status_code == HTTPStatus.UNAUTHORIZED

    token = create_app_token('unauthorized-app')
    r1 = await client.put(
        f'{BASE_URL}/{document_mock.id}',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert r1.status_code == HTTPStatus.UNAUTHORIZED


async def test_update_document_nonexisting(client: AsyncClient, media_processor_token_headers) -> None:
    data = {
        'summary_id': random_uuid_str(),
        'vector_id': random_uuid_str(),
        'extract_duration': random_float(),
        'total_pages': random_integer(),
        'status': 'success',
        'content': None,
    }

    r = await client.put(
        f'{BASE_URL}/{random_uuid()}',
        headers=media_processor_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_create_document(
    httpx_mock: HTTPXMock, client: AsyncClient, normal_user, subscription_mock, normaluser_token_headers
) -> None:
    httpx_mock.add_response(
        method='POST',
        url=f'{settings.MEDIA_PROCESSOR_URL}/v1/text_extract/queue',
        json={'task_id': '11111'},
    )

    with open('tests/data/policy.pdf', 'rb') as f:
        r = await client.post(
            f'{BASE_URL}/policy',
            headers=normaluser_token_headers,
            files={'file': f},
        )
        response = r.json()
        document_id = response['id']
        assert r.status_code == HTTPStatus.CREATED
        assert response['path'] == f'uploads/{normal_user.id}/{document_id}.pdf'
        assert response['size'] is not None

        record = await Document.get_or_none(id=r.json()['id'])
        assert record is not None

        await record.delete()


async def test_create_document_invalid_type(client: AsyncClient, subscription_mock, normaluser_token_headers) -> None:
    with open('tests/data/policy.pdf', 'rb') as f:
        r = await client.post(
            f'{BASE_URL}/policy',
            headers=normaluser_token_headers,
            files={'file': ('filename', f, 'application/png')},
        )
        assert r.status_code == HTTPStatus.UNSUPPORTED_MEDIA_TYPE


async def test_create_document_invalid_product(client: AsyncClient, normaluser_token_headers) -> None:
    with open('tests/data/policy.pdf', 'rb') as f:
        r = await client.post(f'{BASE_URL}/invalid-product', headers=normaluser_token_headers, files={'file': f})
        assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_create_document_media_processor_error(
    httpx_mock: HTTPXMock, client: AsyncClient, subscription_mock, normaluser_token_headers
) -> None:
    httpx_mock.add_response(
        method='POST',
        url=f'{settings.MEDIA_PROCESSOR_URL}/v1/text_extract/queue',
        status_code=500,
        json={'detail': 'Error'},
    )

    with open('tests/data/policy.pdf', 'rb') as f:
        r = await client.post(
            f'{BASE_URL}/policy',
            headers=normaluser_token_headers,
            files={'file': f},
        )

    assert r.status_code == HTTPStatus.CREATED
    assert r.json()['status'] == ExtractionStatus.FAILED_QUEUE


# async def test_delete_document_superuser(client: AsyncClient, superuser_token_headers: dict[str, str]) -> None:
#     document = await document_mock(created_by=random_integer())

#     r = await client.get(
#         f'{BASE_URL}/{document.id}',
#         headers=superuser_token_headers,
#     )
#     assert r.status_code == HTTPStatus.NO_CONTENT


async def test_delete_document(document_mock, client: AsyncClient, normal_user: User, normaluser_token_headers) -> None:
    r = await client.delete(
        f'{BASE_URL}/{document_mock.id}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.NO_CONTENT


async def test_delete_document_nonexisting(client: AsyncClient, normaluser_token_headers) -> None:
    r = await client.delete(
        f'{BASE_URL}/{random_uuid()}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_delete_document_forbidden(client: AsyncClient, document_mock, otheruser_token_headers) -> None:
    r = await client.delete(
        f'{BASE_URL}/{document_mock.id}',
        headers=otheruser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND
