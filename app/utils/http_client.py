import logging

import httpx
from httpx_retries import RetryTransport

logger = logging.getLogger(__name__)


async def request(method: str, url: str, token: str, data):
    # Request with 5 default retries
    async with httpx.AsyncClient(transport=RetryTransport()) as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                headers={'Authorization': f'Bearer {token}'},
                json=data,
            )
            response.raise_for_status()  # Raise an exception for non-2xx status codes
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.exception('A client error occurred: %s', exc.response.json().get('detail'))
            return None
        except Exception:
            logger.exception('External http request error')
            return None


async def post(url: str, token: str, data):
    response = await request('post', url, token, data)
    return response
