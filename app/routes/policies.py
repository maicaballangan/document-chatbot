import json
from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate

from app.core.authentication import check_privileges
from app.core.authentication import CurrentUser
from app.core.responses import conflictResponse
from app.core.responses import notFoundResponse
from app.jobs.background_tasks import document_s3_cleanup
from app.legalai.ai import NewAI
from app.models.document import Document
from app.models.policy import Policy
from app.models.policy import PolicyCreate
from app.models.policy import PolicyOutput
from app.models.policy import PolicyOutputRelated

router = APIRouter()


@router.get(
    '',
    response_model=Page[PolicyOutputRelated],
    status_code=HTTPStatus.OK,
)
async def get_all_policy(current_user: CurrentUser, limit: int = 10, offset: int = 0):
    """
    Get all user policy
    """
    if current_user.is_superuser is True:
        query = Policy.all().limit(limit).offset(offset).prefetch_related('document')
    else:
        query = Policy.filter(created_by=current_user.id).limit(limit).offset(offset).prefetch_related('document')
    return await paginate(query)


@router.get('/{id}', response_model=PolicyOutputRelated, status_code=HTTPStatus.OK, responses={**notFoundResponse})
async def get_policy(id: UUID, current_user: CurrentUser):
    """
    Get record by id
    """
    return await Policy.get(id=id, created_by=current_user.id).prefetch_related('document')


@router.post(
    '',
    response_model=PolicyOutput,
    status_code=HTTPStatus.CREATED,
    responses={**conflictResponse},
)
async def create_policy(current_user: CurrentUser, input: PolicyCreate):
    """
    Create new policy
    """
    exists = await Document.exists(id=input.document_id, created_by=current_user.id)
    if exists is False:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=HTTPStatus.UNPROCESSABLE_ENTITY.phrase,
        )

    exists = await Policy.exists(document_id=input.document_id)
    if exists is True:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=HTTPStatus.CONFLICT.phrase,
        )
    return await Policy.create(created_by=current_user.id, **input.model_dump())


@router.delete('/{id}', status_code=HTTPStatus.NO_CONTENT, responses={**notFoundResponse})
async def delete_policy(id: UUID, current_user: CurrentUser, background_tasks: BackgroundTasks):
    """
    Delete a policy owned by the user
    """
    record = await Policy.get(id=id, created_by=current_user.id).prefetch_related('document')
    await record.delete()

    background_tasks.add_task(document_s3_cleanup, record.document.path, record.document.product)
    await record.document.delete()


@router.put('/{id}/summarize', response_model=PolicyOutput, status_code=HTTPStatus.OK, responses={**notFoundResponse})
async def summarize_policy(id: UUID, current_user: CurrentUser):
    """
    Get record by id
    """
    await check_privileges(current_user, 'policy_analyzer_report_card')

    policy = await Policy.get(id=id, created_by=current_user.id).prefetch_related('document')
    policy_type, summary_dict, report_card_dict = NewAI().summary_the_policy(
        policy.document.id, policy.document.summary_id, policy.document.vector_id
    )

    policy.type = policy_type
    policy.summary = json.dumps(summary_dict)
    policy.report = json.dumps(report_card_dict)

    await policy.save()
    return policy
