from http import HTTPStatus

from fastapi import APIRouter
from fastapi import HTTPException

from app.core.config import settings
from app.core.emails import generate_reset_password_email
from app.core.emails import generate_verification_email
from app.core.emails import send_email
from app.models.base import Email
from app.models.base import Message
from app.models.user import User

router = APIRouter()


@router.get('/health-check')
async def health_check() -> bool:
    return True


@router.post('/resend-verification')
async def resend_verification(body: Email) -> Message:
    """
    Resend Verification Email
    """
    user = await User.get_by_email(body.email)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=HTTPStatus.NOT_FOUND.phrase,
        )
    if user.is_active is True:
        raise HTTPException(
            status_code=HTTPStatus.GONE,
            detail='The user with this email is already verified',
        )
    if settings.emails_enabled and user.email:
        email_data = generate_verification_email(email_to=user.email, first_name=user.first_name)

        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return Message(message='Verification email sent. Please check your inbox')


@router.post('/password-recovery')
async def recover_password(body: Email) -> Message:
    """
    Password Recovery
    """
    user = await User.get_by_email(email=body.email)

    if not user:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=HTTPStatus.NOT_FOUND.phrase,
        )
    email_data = generate_reset_password_email(email_to=user.email, first_name=user.first_name)

    send_email(
        email_to=user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message='Password recovery email sent. Please check your inbox')
