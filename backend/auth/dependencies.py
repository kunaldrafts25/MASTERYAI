from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from backend.auth.jwt import verify_token
from backend.services.learner_store import learner_store

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = await learner_store.get_user_by_id(payload["user_id"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    return user


async def verify_ownership(user: dict, learner_id: str):
    if user.get("learner_id") != learner_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
