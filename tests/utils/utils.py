import datetime
import json
import random
import string
import uuid

from app.core.enums import BillingCycle
from app.core.enums import ChatRole
from app.core.enums import ExtractionStatus
from app.core.enums import ProductType
from app.core.enums import SubscriptionStatus
from app.models.chat import Chat
from app.models.chatsession import ChatSession
from app.models.document import Document
from app.models.policy import Policy
from app.models.subscription import Subscription
from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription_price import SubscriptionPrice
from app.models.user import User
from app.models.user import UserCreateAdmin


def random_lower_string() -> str:
    return ''.join(random.choices(string.ascii_lowercase, k=32))


def random_string() -> str:
    return ''.join(random.choices(string.ascii_letters, k=32))


def random_text() -> str:
    return ''.join(random.choices(string.ascii_letters, k=10000))


def random_integer() -> int:
    return random.randrange(1, 1000)


def random_float() -> float:
    return random.uniform(0.0, 9.9)


def random_uuid() -> uuid.UUID:
    return uuid.uuid4()


def random_uuid_str() -> str:
    return str(uuid.uuid4())


def random_email() -> str:
    return f'{random_lower_string()}@gmail.com'


def random_json():
    return {'test': 1}


def random_bool():
    return random.choice([True, False])


def random_url() -> str:
    return 'https://test.url.net/asdasasd'


def random_date():
    return datetime.datetime.now() + datetime.timedelta(days=random_integer())


async def user_mock() -> User:
    user_in = UserCreateAdmin(
        first_name=random_lower_string(),
        last_name=random_lower_string(),
        email=random_email(),
        password='mockpassword',
        is_active=True,
        is_superuser=False,
    )
    user = await User.create(user=user_in)
    return user


async def inactive_user_mock() -> User:
    user_in = UserCreateAdmin(
        first_name=random_lower_string(),
        last_name=random_lower_string(),
        email=random_email(),
        password='mockpassword',
        is_active=False,
        is_superuser=False,
    )
    return await User.create(user=user_in)


async def document_mock(created_by: int = random_integer()) -> Document:
    return await Document.create(
        name=random_string(),
        product=ProductType.POLICY,
        status=ExtractionStatus.SUCCESS,
        path=random_string(),
        url=random_url(),
        content=random_json(),
        summary=random_json(),
        extract_duration=random_integer(),
        total_pages=random_integer(),
        size=random_integer(),
        retriever_id=random_string(),
        extract_retriever_id=random_string(),
        created_by=created_by,
        task_id=random_string(),
    )


async def policy_mock(document_id=random_uuid(), created_by: int = random_integer()) -> Policy:
    return await Policy.create(
        document_id=document_id,
        name=random_string(),
        filter=random_json(),
        created_by=created_by,
    )


async def policy_chatsession_mock(policy_id=random_uuid(), created_by: int = random_integer()) -> ChatSession:
    document_json = [{'document_id': str(random_uuid())}]
    return await ChatSession.create(
        name=random_lower_string(),
        documents_json=json.dumps(document_json),
        product=ProductType.POLICY,
        product_id=policy_id,
        created_by=created_by,
    )


async def general_chatsession_mock(created_by: int = random_integer()) -> ChatSession:
    document_json = [{'document_id': str(random_uuid())}]
    return await ChatSession.create(
        name=random_lower_string(),
        documents_json=json.dumps(document_json),
        product=ProductType.GENERAL,
        created_by=created_by,
    )


async def chat_mock(session_id=random_uuid(), created_by: int = random_integer()) -> Policy:
    return await Chat.create(
        session_id=session_id,
        content=random_text(),
        role=ChatRole.USER,
        is_liked=random_bool(),
        is_bookmarked=random_bool(),
        source_info=random_json(),
        created_by=created_by,
    )


async def subscription_plan_mock() -> SubscriptionPlan:
    return await SubscriptionPlan.create(
        name=random_string(),
        credits=random_integer(),
        document_limit=random_integer(),
        question_limit=random_integer(),
        storage_limit=random_integer(),
        is_consular=random_bool(),
        trial_period=random_integer(),
        document_size_limit=random_integer(),
        ocr_support=random_bool(),
        chat_with_files=True,
        chat_with_folders=random_bool(),
        invite_team=random_bool(),
        maximum_member=random_integer(),
        policy_analyzer_report_card=True,
        discovery_tool_interrogatories=random_bool(),
        customer_support_email=random_bool(),
        customer_support_phone=random_bool(),
        support_turnaround=random_bool(),
        support_mycase=random_bool(),
        stripe_product_id=f'prod_{random_integer()}',
    )


async def subscription_price_mock(subscription_plan_id=random_integer()) -> SubscriptionPrice:
    return await SubscriptionPrice.create(
        subscription_plan_id=subscription_plan_id,
        billing_cycle=BillingCycle.ANNUAL,
        amount=100.00,
        currency='USD',
        stripe_price_id=f'price_{random_integer()}',
    )


async def subscription_mock(subscription_price_id=random_integer(), user_id: int = random_integer()) -> Subscription:
    return await Subscription.create(
        user_id=user_id,
        subscription_price_id=subscription_price_id,
        status=SubscriptionStatus.ACTIVE,
        current_period_end=random_integer(),
        expired_at=random_date(),
        stripe_subscription_id=f'sub_{random_integer()}',
    )
