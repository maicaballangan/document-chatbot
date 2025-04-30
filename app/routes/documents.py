import uuid
from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import HTTPException
from fastapi import UploadFile
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate

from app.core.authentication import check_privileges
from app.core.authentication import CurrentUser
from app.core.authentication import MediaProcessorApp
from app.core.authentication import SuperUser
from app.core.authentication import TokenDep
from app.core.enums import ExtractionStatus
from app.core.enums import ProductType
from app.core.responses import notFoundResponse
from app.core.responses import uploadErrorResponse
from app.jobs.background_tasks import document_s3_cleanup
from app.models.document import Document
from app.models.document import DocumentAdminOutput
from app.models.document import DocumentOutput
from app.models.document import DocumentUpdate
from app.utils.document_utils import is_valid_file_type
from app.utils.media_processor_client import queue_text_extraction
from app.utils.s3 import S3Service

router = APIRouter()


@router.get(
    '',
    dependencies=[SuperUser],
    response_model=Page[DocumentOutput],
    status_code=HTTPStatus.OK,
)
async def get_all_document(
    limit: int = 100,
    offset: int = 0,
):
    """
    Search all records (SuperUser)
    """
    query = Document.all().limit(limit).offset(offset)
    return await paginate(query)


@router.get('/{id}', response_model=DocumentOutput, status_code=HTTPStatus.OK, responses={**notFoundResponse})
async def get_document(id: UUID, current_user: CurrentUser):
    """
    Get record by id
    """
    return await Document.get(id=id, created_by=current_user.id)


@router.post(
    '/{product}',
    response_model=DocumentOutput,
    status_code=HTTPStatus.CREATED,
    responses={**uploadErrorResponse},
)
async def create_document(
    product: ProductType,
    token: TokenDep,
    file: UploadFile,
    current_user: CurrentUser,
):
    """
    Create new record
    """
    await check_privileges(current_user, 'chat_with_files')

    if not is_valid_file_type(file):
        raise HTTPException(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            detail=HTTPStatus.UNSUPPORTED_MEDIA_TYPE.phrase,
        )

    # s3 upload
    document_id = uuid.uuid4()
    file_suffix = file.filename.rpartition('.')[-1]

    path = f'uploads/{current_user.id}/{document_id}.{file_suffix}'
    url = S3Service().upload_file(file, path, product)

    if not url:
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail=HTTPStatus.SERVICE_UNAVAILABLE.phrase,
        )

    response = await queue_text_extraction(document_id, file.filename, url, token, product)
    if not response:
        # add ability to retry queue extraction
        status = ExtractionStatus.FAILED_QUEUE
        task_id = None
    else:
        status = ExtractionStatus.PENDING
        task_id = response['task_id']

    document = await Document.create(
        id=document_id,
        status=status,
        product=product,
        name=file.filename,
        size=file.size,
        created_by=current_user.id,
        path=path,
        url=url,
        task_id=task_id,
    )

    return document


@router.put(
    '/{id}',
    dependencies=[MediaProcessorApp],
    response_model=DocumentAdminOutput,
    status_code=HTTPStatus.OK,
    responses={**notFoundResponse},
)
async def update_document(id: UUID, input: DocumentUpdate, bg_tasks: BackgroundTasks):
    """
    Media Processor update document content and summary
    """
    record = await Document.get(id=id)

    await record.update_from_dict(input.model_dump()).save()
    return record


@router.delete('/{id}', status_code=HTTPStatus.NO_CONTENT, responses={**notFoundResponse})
async def delete_document(id: UUID, current_user: CurrentUser, background_tasks: BackgroundTasks):
    """
    Delete a document owned by the user
    """
    record = await Document.get(id=id, created_by=current_user.id)
    await record.delete()

    # delete s3 file
    background_tasks.add_task(document_s3_cleanup, record.path, record.product)
