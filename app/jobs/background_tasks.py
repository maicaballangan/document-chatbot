from app.models.chat import Chat
from app.models.chat import ChatCreateInput
from app.utils.s3 import S3Service


async def document_s3_cleanup(path, product):
    S3Service().remove_file(path, product)


async def save_chat(chat: ChatCreateInput):
    await Chat.create(**chat.model_dump())
