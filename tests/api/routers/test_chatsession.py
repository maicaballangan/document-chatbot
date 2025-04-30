from http import HTTPStatus

from httpx import AsyncClient
from httpx import QueryParams

from app.core.config import settings
from app.core.enums import ExtractionStatus
from app.core.enums import ProductType
from app.legalai.ai import NewAI
from app.models.chat import Chat
from app.models.chatsession import ChatSession
from app.models.document import Document
from app.models.policy import Policy
from tests.utils import utils
from tests.utils.utils import chat_mock
from tests.utils.utils import general_chatsession_mock
from tests.utils.utils import policy_chatsession_mock
from tests.utils.utils import random_bool
from tests.utils.utils import random_lower_string
from tests.utils.utils import random_string
from tests.utils.utils import random_text
from tests.utils.utils import random_uuid

BASE_URL = f'{settings.API_V1_STR}/chat_sessions'


async def test_get_all_chatsession_superuser(client: AsyncClient, policy_mock, superuser_token_headers) -> None:
    rec1 = await policy_chatsession_mock(policy_mock.id)
    rec2 = await policy_chatsession_mock(policy_mock.id)
    rec3 = await policy_chatsession_mock(policy_mock.id)
    rec4 = await policy_chatsession_mock(policy_mock.id)
    rec5 = await general_chatsession_mock()

    r = await client.get(BASE_URL, headers=superuser_token_headers, params=QueryParams({'product': 'policy'}))
    results = r.json()

    assert r.status_code == HTTPStatus.OK
    assert len(results['items']) == 4
    assert 'total' in results
    assert 'page' in results
    assert 'size' in results
    assert 'pages' in results

    assert results['total'] == 4

    for item in results['items']:
        assert 'id' in item
        assert 'name' in item
        assert 'product' in item
        assert 'product_id' in item

    await rec1.delete()
    await rec2.delete()
    await rec3.delete()
    await rec4.delete()
    await rec5.delete()


async def test_get_product_chatsession(client: AsyncClient, policy_mock, normal_user, normaluser_token_headers) -> None:
    rec1 = await policy_chatsession_mock(policy_mock.id)
    rec2 = await policy_chatsession_mock(policy_mock.id)
    rec3 = await policy_chatsession_mock(policy_mock.id, normal_user.id)
    rec4 = await policy_chatsession_mock(policy_mock.id, normal_user.id)
    rec5 = await general_chatsession_mock(normal_user.id)

    r = await client.get(
        f'{BASE_URL}',
        headers=normaluser_token_headers,
        params=QueryParams({'product': 'policy', 'product_id': policy_mock.id}),
    )
    results = r.json()

    assert r.status_code == HTTPStatus.OK
    assert len(results['items']) == 2
    assert 'total' in results
    assert 'page' in results
    assert 'size' in results
    assert 'pages' in results

    assert results['total'] == 2

    for item in results['items']:
        assert 'id' in item
        assert 'name' in item
        assert 'product_id' in item

    await rec1.delete()
    await rec2.delete()
    await rec3.delete()
    await rec4.delete()
    await rec5.delete()


async def test_get_chatsession(client: AsyncClient, policy_chatsession_mock, normaluser_token_headers) -> None:
    r = await client.get(
        f'{BASE_URL}/{policy_chatsession_mock.id}',
        headers=normaluser_token_headers,
    )
    result = r.json()

    assert r.status_code == HTTPStatus.OK
    assert result['id'] == str(policy_chatsession_mock.id)
    assert 'name' in result
    assert 'product_id' in result


# # TODO do we need superuser get
# # async def test_get_policy_superuser(client: AsyncClient, superuser_token_headers) -> None:
# #     record = await policy_mock(random_integer())

# #     r = await client.get(
# #         f'{BASE_URL}/{record.id}',
# #         headers=superuser_token_headers,
# #     )
# #     result = r.json()

# #     assert r.status_code == HTTPStatus.OK
# #     assert result['id'] == record.id


async def test_get_chatsession_forbidden(client: AsyncClient, policy_mock, otheruser_token_headers) -> None:
    r = await client.get(
        f'{BASE_URL}/{policy_mock.id}',
        headers=otheruser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_create_chat_session(client: AsyncClient, policy_mock, normaluser_token_headers) -> None:
    data = {
        'product_id': str(policy_mock.id),
        'name': random_lower_string(),
    }

    r = await client.post(
        f'{BASE_URL}/policy',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.CREATED

    record = await ChatSession.get_or_none(id=r.json()['id'])
    assert record is not None

    await record.delete()


async def test_create_chat_session_too_early(client: AsyncClient, normal_user, normaluser_token_headers) -> None:
    document_mock = await Document.create(
        id=random_uuid(),
        name=random_string(),
        product=ProductType.POLICY,
        status=ExtractionStatus.PENDING,
        created_by=normal_user.id,
    )
    policy_mock = await utils.policy_mock(document_mock.id, normal_user.id)

    data = {
        'product_id': str(policy_mock.id),
        'name': random_lower_string(),
    }
    r = await client.post(
        f'{BASE_URL}/policy',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.TOO_EARLY
    await policy_mock.delete()
    await document_mock.delete()


async def test_create_chatsession_duplicate_policy(client: AsyncClient, policy_mock, normaluser_token_headers) -> None:
    data = {
        'product_id': str(policy_mock.id),
        'name': random_lower_string(),
    }
    r = await client.post(
        f'{BASE_URL}/policy',
        headers=normaluser_token_headers,
        json=data,
    )

    await client.post(
        f'{BASE_URL}/policy',
        headers=normaluser_token_headers,
        json=data,
    )

    assert r.status_code == HTTPStatus.CREATED
    record = await ChatSession.get_or_none(id=r.json()['id'])
    assert record is not None

    await record.delete()


async def test_delete_chatsession(
    client: AsyncClient, policy_chatsession_mock, policy_mock, normaluser_token_headers
) -> None:
    r = await client.delete(
        f'{BASE_URL}/{policy_chatsession_mock.id}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.NO_CONTENT

    # Policy should not be deleted
    assert await Policy.exists(id=policy_mock.id) is True


async def test_delete_chatsession_cascade_chat_delete(
    client: AsyncClient, policy_chatsession_mock, chat_mock, normaluser_token_headers
) -> None:
    assert await Chat.exists(id=chat_mock.id) is True

    r = await client.delete(
        f'{BASE_URL}/{policy_chatsession_mock.id}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.NO_CONTENT

    # chat should be cascade deleted
    assert await Chat.exists(id=chat_mock.id) is False


async def test_delete_chatsession_nonexisting(client: AsyncClient, normaluser_token_headers) -> None:
    r = await client.delete(
        f'{BASE_URL}/{random_uuid()}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_delete_chatsession_forbidden(
    client: AsyncClient, policy_chatsession_mock, otheruser_token_headers
) -> None:
    r = await client.delete(
        f'{BASE_URL}/{policy_chatsession_mock.id}',
        headers=otheruser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


## Chat
async def test_get_all_session_chat(
    client: AsyncClient, policy_chatsession_mock, normal_user, normaluser_token_headers
) -> None:
    general_chatsession = await general_chatsession_mock(normal_user.id)
    rec1 = await chat_mock(policy_chatsession_mock.id, normal_user.id)
    rec2 = await chat_mock(policy_chatsession_mock.id, normal_user.id)
    rec3 = await chat_mock(policy_chatsession_mock.id, normal_user.id)
    rec4 = await chat_mock(general_chatsession.id)
    rec5 = await chat_mock(policy_chatsession_mock.id)

    r = await client.get(f'{BASE_URL}/{policy_chatsession_mock.id}/chats', headers=normaluser_token_headers)
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
        assert 'content' in item
        assert 'role' in item
        assert 'response_to' in item
        assert 'is_liked' in item
        assert 'is_bookmarked' in item
        assert 'source_info' in item

    await rec1.delete()
    await rec2.delete()
    await rec3.delete()
    await rec4.delete()
    await rec5.delete()
    await general_chatsession.delete()


async def test_get_session_chat(
    client: AsyncClient, policy_chatsession_mock, chat_mock, normaluser_token_headers
) -> None:
    r = await client.get(
        f'{BASE_URL}/{policy_chatsession_mock.id}/chats/{chat_mock.id}',
        headers=normaluser_token_headers,
    )
    result = r.json()

    assert r.status_code == HTTPStatus.OK
    assert result['id'] == str(chat_mock.id)
    assert 'content' in result
    assert 'role' in result
    assert 'response_to' in result
    assert 'is_liked' in result
    assert 'is_bookmarked' in result
    assert 'source_info' in result


async def test_get_session_chat_forbidden(
    client: AsyncClient, policy_chatsession_mock, chat_mock, otheruser_token_headers
) -> None:
    r = await client.get(
        f'{BASE_URL}/{policy_chatsession_mock.id}/chats/{chat_mock.id}',
        headers=otheruser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_create_session_chat(
    client: AsyncClient, chat_mock, policy_chatsession_mock, normaluser_token_headers, monkeypatch
) -> None:
    def mock_chat_stream(
        self,
        documents_json: dict,
        latest_user_new_chat: str,
        chat_history: list[Chat],
        session_id,
        response_to,
        product: ProductType,
        bg_tasks,
    ):
        yield 'event: stream-start'
        yield 'data: { "content": "hello this is a mock" }'
        yield 'event: stream-end'

    monkeypatch.setattr(NewAI, 'chat_stream_response', mock_chat_stream)

    data = {'content': random_text(), 'response_to': str(chat_mock.id)}
    r = await client.post(
        f'{BASE_URL}/{policy_chatsession_mock.id}/chats',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.CREATED
    assert r.stream is not None


async def test_create_session_chat_integrity_error(client: AsyncClient, otheruser_token_headers) -> None:
    data = {
        'content': random_text(),
    }
    r = await client.post(
        f'{BASE_URL}/{random_uuid()}/chats',
        headers=otheruser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


async def test_update_session_chat_like(
    client: AsyncClient, chat_mock, policy_chatsession_mock, normaluser_token_headers
) -> None:
    data = {
        'is_liked': random_bool(),
    }
    r = await client.put(
        f'{BASE_URL}/{policy_chatsession_mock.id}/chats/{chat_mock.id}/like',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.OK


async def test_update_session_chat_bookmark(
    client: AsyncClient, chat_mock, policy_chatsession_mock, normaluser_token_headers
) -> None:
    data = {
        'is_bookmarked': random_bool(),
    }
    r = await client.put(
        f'{BASE_URL}/{policy_chatsession_mock.id}/chats/{chat_mock.id}/bookmark',
        headers=normaluser_token_headers,
        json=data,
    )
    assert r.status_code == HTTPStatus.OK


async def test_delete_session_chat(
    client: AsyncClient, policy_chatsession_mock, chat_mock, normaluser_token_headers
) -> None:
    r = await client.delete(
        f'{BASE_URL}/{policy_chatsession_mock.id}/chats/{chat_mock.id}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.NO_CONTENT


async def test_delete_session_chat_nonexisting(
    client: AsyncClient, policy_chatsession_mock, normaluser_token_headers
) -> None:
    r = await client.delete(
        f'{BASE_URL}/{policy_chatsession_mock.id}/chats/{random_uuid()}',
        headers=normaluser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND


async def test_delete_session_chat_forbidden(
    client: AsyncClient, policy_chatsession_mock, chat_mock, otheruser_token_headers
) -> None:
    r = await client.delete(
        f'{BASE_URL}/{policy_chatsession_mock.id}/chats/{chat_mock.id}',
        headers=otheruser_token_headers,
    )
    assert r.status_code == HTTPStatus.NOT_FOUND
