from http import HTTPStatus
from typing import Annotated

from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User
from app.utils import security

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f'{settings.API_V1_STR}/login')

TokenDep = Annotated[str, Depends(reusable_oauth2)]


async def get_current_user(token: TokenDep) -> User:
    user_id = security.verify_token(token, 'access')
    if user_id is None:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=HTTPStatus.UNAUTHORIZED.phrase)
    user = await User.get_or_none(id=user_id)
    if user is None or user.is_active is False:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=HTTPStatus.UNAUTHORIZED.phrase)
    return user


async def get_current_user_from_email(token: str) -> User:
    email = security.verify_token(token, 'email')
    if email is None:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=HTTPStatus.UNAUTHORIZED.phrase)
    user = await User.get_by_email(email=email)
    if user is None:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=HTTPStatus.UNAUTHORIZED.phrase)
    return user


async def media_processor_access(token: TokenDep):
    app_id = security.verify_app(token)
    if app_id is None or app_id != 'media-processor':
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail=HTTPStatus.UNAUTHORIZED.phrase)


CurrentUser = Annotated[User, Depends(get_current_user)]
UserFromEmailToken = Annotated[User, Depends(get_current_user_from_email)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
    if current_user.is_superuser is False:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail=HTTPStatus.FORBIDDEN.phrase)
    return current_user


async def check_privileges(
    current_user: User,
    privilege: str,
) -> User:
    if not current_user.is_superuser:
        # Fetch the user's subscription
        subscription = await Subscription.get_or_none(
            user_id=current_user.id, status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]
        )
        if not subscription:
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='No active subscription found.')

        # Fetch the subscription plan
        subscription_plan = await SubscriptionPlan.get_or_none(id=subscription.subscription_price_id)
        if not subscription_plan:
            raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail='Subscription plan not found.')

        # Check if the required privilege is available in the subscription plan
        if privilege and not getattr(subscription_plan, privilege, False):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail=f'Access denied. Required privilege: {privilege}.'
            )

    return current_user


NormalUser = Depends(get_current_user)
SuperUser = Depends(get_current_active_superuser)
MediaProcessorApp = Depends(media_processor_access)
