from datetime import datetime
from datetime import timedelta
from datetime import timezone

import jwt
from passlib.hash import django_pbkdf2_sha256 as handler

from app.core.config import settings

ALGORITHM = 'HS256'


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return handler.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return handler.hash(password)


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {
        'exp': expire,
        'iat': datetime.now(timezone.utc),
        'user_id': user_id,
        'token_type': 'access'
    }

    encoded_jwt: str = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {'exp': expire, 'user_id': user_id, 'token_type': 'refresh'}
    encoded_jwt: str = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_email_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_TOKEN_EXPIRE_HOURS)
    now = datetime.now(timezone.utc)
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {'exp': exp, 'nbf': now, 'user_id': email, 'token_type': 'email'},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    return encoded_jwt


def verify_token(token: str, type: str) -> str | None:
    """
    Verify a JWT token and return TokenData if valid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload['user_id']
        if sub is None or payload['token_type'] != type:
            return None
        else:
            return sub

    except Exception:
        return None


def create_app_token(app_id: str) -> str:
    to_encode = {
        'app_id': app_id,
        'token_type': 'access',
    }
    encoded_jwt: str = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_app(token: str) -> str | None:
    """
    Verify a JWT token for app and return TokenData if valid
    """
    #  { 'app_id': 'media-processor', 'token_type': 'access' }
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload['app_id']
        if sub is None or payload['token_type'] != 'access':  # noqa
            return None
        else:
            return sub

    except Exception:
        return None
