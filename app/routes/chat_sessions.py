import json
from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import HTTPException
from fastapi import Query
from fastapi.responses import StreamingResponse
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate

from app.core.authentication import CurrentUser
from app.core.enums import ChatRole
from app.core.enums import ExtractionStatus
from app.core.enums import ProductType
from app.core.responses import notFoundResponse
from app.core.responses import tooEarlyResponse
from app.legalai.ai import NewAI
from app.models.chat import Chat
from app.models.chat import ChatBookmarkUpdate
from app.models.chat import ChatCreateInput
from app.models.chat import ChatLikeUpdate
from app.models.chat import ChatOutput
from app.models.chatsession import ChatSession
from app.models.chatsession import ChatSessionAdminOutput
from app.models.chatsession import ChatSessionInput
from app.models.chatsession import ChatSessionOutput
from app.models.chatsession import ChatSessionRelatedOutput
from app.models.document import Document
from app.models.policy import Policy

router = APIRouter()


@router.get(
    '',
    response_model=Page[ChatSessionAdminOutput],
    status_code=HTTPStatus.OK,
)
async def get_all_chat_session(
    current_user: CurrentUser,
    product: ProductType,
    product_id: UUID = Query(default=None, alias='product_id'),
    limit: int = 100,
    offset: int = 0,
):
    """
    Retrieve chat sessions
    """
    query = ChatSession.filter(product=product)

    if product_id is not None:
        query = query.filter(product_id=product_id)

    if current_user.is_superuser is False:
        query = query.filter(created_by=current_user.id)

    query = query.all().limit(limit).offset(offset).order_by('-created_at')
    return await paginate(query)


@router.get('/{id}', response_model=ChatSessionRelatedOutput, status_code=HTTPStatus.OK, responses={**notFoundResponse})
async def get_chat_session(
    id: UUID,
    current_user: CurrentUser,
):
    """
    Get record by id
    """
    return await ChatSession.get(id=id, created_by=current_user.id).prefetch_related('shared_with')


@router.post(
    '/{product}', response_model=ChatSessionOutput, status_code=HTTPStatus.CREATED, responses={**tooEarlyResponse}
)
async def create_chat_session(
    product: ProductType,
    current_user: CurrentUser,
    input: ChatSessionInput,
):
    """
    Create record
    """
    documents_json = []
    document_processing_fail = False

    match product:
        case ProductType.GENERAL:
            for document_id in input.document_ids:
                document = await Document.get(id=document_id, created_by=current_user.id)
                if document.status != ExtractionStatus.SUCCESS:
                    document_processing_fail = True

                documents_json.append({'vector_id': document.vector_id, 'summary_id': document.summary_id})
        case ProductType.POLICY:
            reference = await Policy.get(id=input.product_id, created_by=current_user.id).prefetch_related('document')
            if reference.document.status != ExtractionStatus.SUCCESS:
                document_processing_fail = True

            documents_json.append({
                'vector_id': reference.document.vector_id,
                'summary_id': reference.document.summary_id,
            })

    if document_processing_fail is True:
        raise HTTPException(
            status_code=HTTPStatus.TOO_EARLY,
            detail='The document(s) were not yet processed',
        )
    record = await ChatSession.create(
        documents_json=json.dumps(documents_json),
        created_by=current_user.id,
        product=product.value,
        **input.model_dump(),
    )

    return record


@router.delete('/{id}', status_code=HTTPStatus.NO_CONTENT, responses={**notFoundResponse})
async def remove_chat_session(id: UUID, current_user: CurrentUser):
    """
    Delete record
    """
    record = await ChatSession.get(id=id, created_by=current_user.id)
    await record.delete()


@router.get(
    '/{id}/chats',
    response_model=Page[ChatOutput],
    status_code=HTTPStatus.OK,
)
async def get_all_session_chat(
    id: UUID,
    current_user: CurrentUser,
    limit: int = 100,
    offset: int = 0,
):
    """
    Get all session chats
    """
    query = Chat.filter(session_id=id, created_by=current_user.id).all().limit(limit).offset(offset)
    return await paginate(query)


@router.get(
    '/{id}/chats/{chat_id}', response_model=ChatOutput, status_code=HTTPStatus.OK, responses={**notFoundResponse}
)
async def get_session_chat(id: UUID, chat_id: UUID, current_user: CurrentUser):
    """
    Get record by id
    """
    return await Chat.get(id=chat_id, session_id=id, created_by=current_user.id)


@router.post('/{id}/chats', response_model=ChatOutput, status_code=HTTPStatus.CREATED)
async def create_session_chat(id: UUID, input: ChatCreateInput, current_user: CurrentUser, bg_tasks: BackgroundTasks):
    """
    Create chat
    """
    chat = await Chat.create(
        **input.model_dump(),
        session_id=id,
        role=ChatRole.USER.value,
    )

    session = await ChatSession.get(id=id, created_by=current_user.id)
    chats = await Chat.filter(session_id=id).order_by('created_at')

    stream = NewAI().chat_stream_response(
        documents_json=session.documents_json,
        latest_user_new_chat=input.content,
        chat_history=chats,
        session_id=id,
        response_to=chat.id,
        product=session.product,
        bg_tasks=bg_tasks,
    )
    return StreamingResponse(stream, status_code=HTTPStatus.CREATED, media_type='text/event-stream')


@router.put(
    '/{id}/chats/{chat_id}/like', response_model=ChatOutput, status_code=HTTPStatus.OK, responses={**notFoundResponse}
)
async def update_session_chat_like(id: UUID, chat_id: UUID, input: ChatLikeUpdate, current_user: CurrentUser):
    """
    Like the chat
    """
    record = await Chat.get(id=chat_id, session_id=id, created_by=current_user.id)
    record.is_liked = input.is_liked

    await record.save()
    return record


@router.put(
    '/{id}/chats/{chat_id}/bookmark',
    response_model=ChatOutput,
    status_code=HTTPStatus.OK,
    responses={**notFoundResponse},
)
async def update_session_chat_bookmark(id: UUID, chat_id: UUID, input: ChatBookmarkUpdate, current_user: CurrentUser):
    """
    Bookmark the chat
    """
    record = await Chat.get(id=chat_id, session_id=id, created_by=current_user.id)
    record.is_bookmarked = input.is_bookmarked

    await record.save()
    return record


@router.delete('/{id}/chats/{chat_id}', status_code=HTTPStatus.NO_CONTENT, responses={**notFoundResponse})
async def remove_session_chat(id: UUID, chat_id: UUID, current_user: CurrentUser):
    """
    Delete a chat owned by the user
    """
    record = await Chat.get(id=chat_id, session_id=id, created_by=current_user.id)
    await record.delete()
