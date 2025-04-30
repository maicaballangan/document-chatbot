import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import emails  # type: ignore
from jinja2 import Template

from app.core.config import settings
from app.utils.security import create_email_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (Path(__file__).resolve().parent.parent / 'email-templates' / 'build' / template_name).read_text()
    html_content = Template(template_str).render(context)
    return html_content


def send_email(
    *,
    email_to: str,
    subject: str = '',
    html_content: str = '',
) -> None:
    if not settings.emails_enabled:
        logger.error('no provided configuration for email variables')

    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    smtp_options = {'host': settings.SMTP_HOST, 'port': settings.SMTP_PORT}
    if settings.SMTP_TLS:
        smtp_options['tls'] = True
    elif settings.SMTP_SSL:
        smtp_options['ssl'] = True
    if settings.SMTP_USER:
        smtp_options['user'] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options['password'] = settings.SMTP_PASSWORD
    response = message.send(to=email_to, smtp=smtp_options)
    logger.info(f'send email result: {response}')


def generate_verification_email(email_to: str, first_name: str) -> EmailData:
    token = create_email_token(email_to)
    link = f'{settings.FRONTEND_HOST}/verify-email/{token}/confirm'

    subject = 'Email Verification'
    html_content = render_email_template(
        template_name='email_verification.html',
        context={
            'name': first_name,
            'verify_email_url': link,
            'expiration_hours': settings.EMAIL_TOKEN_EXPIRE_HOURS,
            'policy_pro_trial': False,  # TODO what is this?
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_welcome_email(first_name: str) -> EmailData:
    link = f'{settings.FRONTEND_HOST}/settings/billing-subscription'

    subject = 'Welcome to Your Free Trial!'
    html_content = render_email_template(
        template_name='welcome_trial.html',
        context={
            'name': first_name,
            'subscription_url': link,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_remove_account_email(email_to: str, first_name: str) -> EmailData:
    token = create_email_token(email_to)
    link = f'{settings.FRONTEND_HOST}/verify-remove-account/{token}/confirm'

    subject = 'Deactivate Account'
    html_content = render_email_template(
        template_name='remove_account.html',
        context={
            'name': first_name,
            'remove_account_url': link,
            'expiration_hours': settings.EMAIL_TOKEN_EXPIRE_HOURS,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_remove_account_success_email(first_name: str) -> EmailData:
    subject = 'Deactivate Account Complete'
    html_content = render_email_template(
        template_name='remove_account_success.html',
        context={
            'name': first_name,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(email_to: str, first_name: str) -> EmailData:
    token = create_email_token(email_to)
    link = f'{settings.FRONTEND_HOST}/reset-password/{token}/confirm'

    subject = 'Password Reset'
    html_content = render_email_template(
        template_name='remove_account.html',
        context={
            'name': first_name,
            'reset_password_url': link,
            'expiration_hours': settings.EMAIL_TOKEN_EXPIRE_HOURS,
        },
    )
    return EmailData(html_content=html_content, subject=subject)
