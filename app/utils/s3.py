import logging
from shlex import quote

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import settings
from app.core.enums import ProductType

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            # aws_session_token=settings.AWS_SESSION_TOKEN,
            region_name=settings.AWS_REGION_NAME,
        )

        self.bucket_mapping = {
            'general': (settings.GENERAL_BUCKET_DOMAIN, settings.GENERAL_BUCKET),
            'policy': (settings.POLICY_BUCKET_DOMAIN, settings.POLICY_BUCKET),
            'discovery': (settings.DISCOVERY_BUCKET_DOMAIN, settings.DISCOVERY_BUCKET),
            #'avatar': (settings.AVATAR_BUCKET_DOMAIN, settings.AVATAR_BUCKET),
            'archive': (settings.ARCHIVE_BUCKET_DOMAIN, settings.ARCHIVE_BUCKET),
        }

    def handle_bucket(self, module):
        if module in self.bucket_mapping:
            return self.bucket_mapping[module]
        else:
            return None

    def encode_s3_url(self, bucket_name, object_name):
        # URL encode the object name to handle special characters
        encoded_object_name = quote(object_name)
        return f'https://{bucket_name}/{encoded_object_name}'

    def upload_file(self, file: UploadFile, upload_path: str, product: ProductType):
        # TODO: change S3 bucket to private and use cloudflare zero trust/ cloud front
        try:
            bucket = self.handle_bucket(product.value)
            self.client.upload_fileobj(
                file.file._file,
                bucket[1],
                upload_path,
                ExtraArgs={
                    # 'ACL': 'public-read',  # or any other ACL as per your requirement
                    'ContentType': file.content_type,
                    'ContentDisposition': 'inline',
                },
            )
            return self.encode_s3_url(bucket[0], upload_path)
        except ClientError as e:
            logger.exception('A client error occurred: %s', e.__cause__)
            return None

    def remove_file(self, upload_path: str, product: ProductType):
        bucket = self.handle_bucket(product.value)
        try:
            self.client.delete_object(Bucket=bucket[1], Key=upload_path)
            return True
        except ClientError as e:
            logger.exception('A client error occurred: %s', e.__cause__)
            return False
        except Exception as e:
            logger.exception('Caught unhandled exception: %s', e.__cause__)
            return False

    # def archive_file(self, url):
    #     extracted_info = self.handle_bucket_by_domain(url)
    #     if extracted_info is None:
    #         return False

    #     try:
    #         copy_source = {'Bucket': extracted_info[0], 'Key': extracted_info[1]}
    #         self.client.copy(copy_source, settings.ARCHIVE_BUCKET, f'{extracted_info[0]}/{extracted_info[1]}')
    #         self.client.delete_object(Bucket=extracted_info[0], Key=extracted_info[1])
    #         return True
    #     except ClientError as e:
    #         logger.exception('A client error occurred: %s', e.__cause__)
    #         return False
    #     except Exception as e:
    #         logger.exception('Caught unhandled exception: %s', e.__cause__)
    #         return False
