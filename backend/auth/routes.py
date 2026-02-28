import uuid
import logging
import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr
from backend.auth.jwt import create_token
from backend.services.learner_store import learner_store
from backend.models.learner import LearnerState, LearningProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    name: str = Field(min_length=1, max_length=100)
    experience_level: str = "beginner"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
async def register(req: RegisterRequest):
    existing = await learner_store.get_user_by_email(req.email)
    if existing:
        raise HTTPException(409, "Email already registered")

    user_id = str(uuid.uuid4())
    learner_id = str(uuid.uuid4())
    password_hash = hash_password(req.password)

    learner = LearnerState(
        learner_id=learner_id,
        name=req.name,
        experience_level=req.experience_level,
        learning_profile=LearningProfile(),
    )
    await learner_store.create_learner(learner)
    await learner_store.create_user(user_id, req.email, password_hash, learner_id)

    token = create_token(user_id, req.email)
    logger.info(f"registered user {req.email} -> {user_id}")
    return {
        "token": token,
        "user_id": user_id,
        "learner_id": learner_id,
        "name": req.name,
    }


@router.post("/login")
async def login(req: LoginRequest):
    user = await learner_store.get_user_by_email(req.email)
    if not user or not check_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    # fetch learner to get name
    learner = await learner_store.get_learner(user["learner_id"]) if user.get("learner_id") else None

    token = create_token(user["user_id"], req.email)
    logger.info(f"login: {req.email}")
    return {
        "token": token,
        "user_id": user["user_id"],
        "learner_id": user["learner_id"],
        "name": learner.name if learner else "",
    }
