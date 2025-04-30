import hashlib
from urllib.parse import urlencode

from fastapi import requests


def get_gravatar_url(email):
    size = 256

    # Encode the email to lowercase and then to bytes
    email_encoded = email.lower().encode('utf-8')

    # Generate the SHA256 hash of the email
    email_hash = hashlib.sha256(email_encoded).hexdigest()

    # Construct the URL with encoded query parameters
    query_params = urlencode({'d': 404, 's': str(size)})
    gravatar_url = f'https://www.gravatar.com/avatar/{email_hash}?{query_params}'
    # check exist avatar uploaded
    res = requests.get(gravatar_url, timeout=10)
    if res.status_code == 404:
        return None
    else:
        return gravatar_url
