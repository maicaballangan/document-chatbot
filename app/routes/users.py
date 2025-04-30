from http import HTTPStatus

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate

from app.core import emails
from app.core.authentication import CurrentUser
from app.core.authentication import SuperUser
from app.core.authentication import UserFromEmailToken
from app.core.config import settings
from app.models.user import ResetPassword
from app.models.user import UpdatePassword
from app.models.user import User
from app.models.user import UserCreate
from app.models.user import UserOutput
from app.models.user import UserOutputPublic
from app.models.user import UserUpdate
from app.utils.security import get_password_hash
from app.utils.security import verify_password

router = APIRouter()


@router.post('/register', response_model=UserOutput, status_code=HTTPStatus.CREATED)
async def register_user(
    *,
    user_in: UserCreate,
):
    """
    Create new user.
    """
    existing_user = await User.get_by_email(email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='The user with this email already exists in the system',
        )

    user = await User.create(user_in)

    if settings.emails_enabled and user_in.email:
        email_data = emails.generate_verification_email(email_to=user.email, first_name=user.first_name)

        emails.send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


@router.get('/current', response_model=UserOutputPublic, status_code=HTTPStatus.OK)
def get_current_user(
    current_user: CurrentUser,
):
    """
    Get current user.
    """
    return current_user


@router.put('/current/password', status_code=HTTPStatus.NO_CONTENT)
async def update_current_user_password(user_in: UpdatePassword, current_user: CurrentUser):
    """
    Update own password.
    """
    if verify_password(user_in.old_password, current_user.password) is False:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Incorrect password')

    current_user.password = get_password_hash(user_in.new_password_1)
    await current_user.save()


@router.put('/current', response_model=UserOutputPublic, status_code=HTTPStatus.OK)
async def update_current_user(user_in: UserUpdate, current_user: CurrentUser):
    """
    Update own user.
    """
    await current_user.update_from_dict(user_in.model_dump()).save()
    return current_user


@router.delete('/current', status_code=HTTPStatus.ACCEPTED)
async def remove_current_user(current_user: CurrentUser):
    """
    Create deactivate email
    """
    if settings.emails_enabled and current_user.email:
        email_data = emails.generate_remove_account_email(
            email_to=current_user.email, first_name=current_user.first_name
        )

        emails.send_email(
            email_to=current_user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )


@router.get(
    '',
    dependencies=[SuperUser],
    response_model=Page[UserOutput],
    status_code=HTTPStatus.OK,
)
async def get_all_user(
    limit: int = 100,
    offset: int = 0,
):
    """
    Search all records records (SuperUser)
    """
    query = User.all().limit(limit).offset(offset)
    return await paginate(query)


@router.get(
    '/{id}',
    dependencies=[SuperUser],
    response_model=UserOutput,
    status_code=HTTPStatus.OK,
)
async def get_user(
    id: int,
):
    """
    Get a specific user by id (SuperUser)
    """
    return await User.get(id=id)


@router.post(
    '',
    dependencies=[SuperUser],
    response_model=UserOutput,
    status_code=HTTPStatus.CREATED,
)
async def create_user(*, user_in: UserCreate):
    """
    Create new user (SuperUser)
    """
    existing_user = await User.get_by_email(email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='The user with this username already exists in the system',
        )

    user = await User.create(user_in)
    return user


@router.put(
    '/{id}',
    dependencies=[SuperUser],
    response_model=UserOutput,
    status_code=HTTPStatus.OK,
)
async def update_user(
    id: int,
    user_in: UserUpdate,
):
    """
    Update a user (SuperUser)
    """
    user = await User.get(id=id)
    await user.update_from_dict(user_in.model_dump()).save()
    return user


@router.delete(
    '/{id}',
    dependencies=[SuperUser],
    status_code=HTTPStatus.NO_CONTENT,
)
async def remove_user(id: int):
    """
    Delete a user (SuperUser)
    """
    user = await User.get(id=id)
    await user.delete()


@router.post('/verify-email', status_code=HTTPStatus.NO_CONTENT)
async def user_verify_email(user: UserFromEmailToken):
    """
    Verify email
    """
    if user.is_active is True:
        raise HTTPException(
            status_code=HTTPStatus.GONE,
            detail='The user with this email is already verified',
        )
    user.is_active = True
    await user.save()

    if settings.emails_enabled and user.email:
        email_data = emails.generate_welcome_email(first_name=user.first_name)

        emails.send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )


@router.post('/reset-password', status_code=HTTPStatus.NO_CONTENT)
async def user_reset_password(body: ResetPassword, user: UserFromEmailToken):
    """
    Reset password
    """
    if user.is_active is False:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=HTTPStatus.FORBIDDEN.phrase)
    hashed_password = get_password_hash(password=body.new_password_1)
    user.password = hashed_password

    await user.save()


@router.post('/verify-delete', status_code=HTTPStatus.NO_CONTENT)
async def user_verify_delete(user: UserFromEmailToken):
    """
    Deactivate user
    """
    await user.delete()

    if settings.emails_enabled and user.email:
        email_data = emails.generate_remove_account_success_email(first_name=user.first_name)

        emails.send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
