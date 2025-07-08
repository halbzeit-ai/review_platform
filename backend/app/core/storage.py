
from boto3.session import Session
from botocore.config import Config
from ..core.config import settings

def get_s3_client():
    session = Session()
    return session.client('s3',
        endpoint_url=settings.DO_SPACES_ENDPOINT,
        config=Config(s3={'addressing_style': 'virtual'}),
        region_name=settings.DO_SPACES_REGION,
        aws_access_key_id=settings.DO_SPACES_KEY,
        aws_secret_access_key=settings.DO_SPACES_SECRET
    )
