import logging
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from backend.config import settings

logger = logging.getLogger(__name__)

_jwt_secret: str | None = None


def _get_jwt_secret() -> str:
    global _jwt_secret
    if _jwt_secret is not None:
        return _jwt_secret
    if settings.aws_jwt_secret_arn:
        try:
            import boto3
            sm = boto3.client("secretsmanager", region_name=settings.aws_region)
            resp = sm.get_secret_value(SecretId=settings.aws_jwt_secret_arn)
            _jwt_secret = resp["SecretString"]
            logger.info("loaded JWT secret from Secrets Manager")
            return _jwt_secret
        except Exception as e:
            logger.warning("Secrets Manager failed, using config: %s", e)
    _jwt_secret = settings.jwt_secret
    return _jwt_secret


def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[settings.jwt_algorithm])
        return {"user_id": payload["sub"], "email": payload["email"]}
    except JWTError:
        return None
