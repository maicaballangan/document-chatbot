from uuid import UUID

from app.core.config import settings
from app.core.enums import ProductType
from app.utils import http_client


async def queue_text_extraction(
    document_id: UUID, document_name: str, url: str, token: str, product: ProductType
) -> str | None:
    data = {'document_id': str(document_id), 'document_name': document_name, 'url': url, 'product': product.value}
    json = await http_client.post(f'{settings.MEDIA_PROCESSOR_URL}/v1/text_extract/queue', token, data)
    return json


# async def get_extraction_status(task_id: str, token: str) -> str | None:
#     json = await http_client.post(f'{settings.MEDIA_PROCESSOR_URL}/text_extraction_status/{task_id}', token)

#     if json:
#         return json['status']
#     else:
#         return None
