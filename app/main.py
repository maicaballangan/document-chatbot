from asyncio.log import logger
from contextlib import asynccontextmanager
from http import HTTPStatus

import sentry_sdk
import stripe
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.routing import APIRouter
from fastapi_pagination import add_pagination
from stripe import StripeError
from tortoise import Tortoise
from tortoise.exceptions import DoesNotExist
from tortoise.exceptions import IntegrityError

from app.core.config import settings
from app.routes import auths
from app.routes import chat_sessions
from app.routes import documents
from app.routes import policies
from app.routes import subscription_plans
from app.routes import subscription_prices
from app.routes import subscriptions
from app.routes import users
from app.routes import utils
from app.routes import webhooks


def custom_generate_unique_id(route: APIRoute) -> str:
    return f'{route.tags[0]}-{route.name}'


if settings.SENTRY_DSN and settings.ENVIRONMENT != 'local':
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

# setup database
MODELS = [
    'aerich.models',
    'app.models.user',
    'app.models.document',
    'app.models.policy',
    'app.models.chatsession',
    'app.models.chat',
    'app.models.subscription_plan',
    'app.models.subscription_price',
    'app.models.subscription',
    'app.models.invoice',
]

TORTOISE_ORM = {
    'connections': {
        # Dict format for connection
        'default': {
            'engine': 'tortoise.backends.asyncpg',
            'credentials': {
                'host': settings.POSTGRES_SERVER,
                'port': settings.POSTGRES_PORT,
                'user': settings.POSTGRES_USER,
                'password': settings.POSTGRES_PASSWORD,
                'database': settings.POSTGRES_DB,
            },
        }
    },
    'apps': {'app': {'models': MODELS}},
    'use_tz': False,
    'timezone': 'UTC',
}

stripe.api_key = settings.STRIPE_SECRET_KEY


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register Tortoise ORM
    await Tortoise.init(
        config=TORTOISE_ORM,
    )

    # Generate the schema
    await Tortoise.generate_schemas()  # TODO remove for production
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f'{settings.API_V1_STR}/openapi.json',
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

api_router = APIRouter()
api_router.include_router(utils.router, tags=['utils'])
api_router.include_router(auths.router, tags=['auth'])
api_router.include_router(users.router, prefix='/users', tags=['users'])
api_router.include_router(documents.router, prefix='/documents', tags=['documents'])
api_router.include_router(policies.router, prefix='/policies', tags=['policies'])
api_router.include_router(chat_sessions.router, prefix='/chat_sessions', tags=['chat_sessions'])
api_router.include_router(subscriptions.router, prefix='/subscriptions', tags=['subscriptions'])
api_router.include_router(subscription_plans.router, prefix='/subscription_plans', tags=['subscription_plans'])
api_router.include_router(subscription_prices.router, prefix='/subscription_prices', tags=['subscription_prices'])
api_router.include_router(webhooks.router, prefix='/webhooks', tags=['webhooks'])

app.include_router(api_router, prefix=settings.API_V1_STR)
add_pagination(app)


# Global Exception
@app.exception_handler(DoesNotExist)
async def notfound_exception_handler(request, e):
    raise HTTPException(
        status_code=HTTPStatus.NOT_FOUND,
        detail=HTTPStatus.NOT_FOUND.phrase,
    )


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request, e):
    logger.warning('Data integrity error has occurred: %s', e)
    raise HTTPException(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        detail=HTTPStatus.UNPROCESSABLE_ENTITY.phrase,
    )


@app.exception_handler(StripeError)
async def stripe_error_handler(request, e: StripeError):
    logger.warning('A Stripe error occurred: %s', e)
    raise HTTPException(
        status_code=HTTPStatus.BAD_REQUEST,
        detail=e.json_body,
    )


# Global Exception
@app.exception_handler(Exception)
async def error_handler(request, e: Exception):
    logger.exception('An unhandled error occurred!')
    raise HTTPException(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        detail=HTTPStatus.INTERNAL_SERVER_ERROR.phrase,
    )
