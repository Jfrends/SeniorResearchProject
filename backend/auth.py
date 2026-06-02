from datetime import datetime, timedelta
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    OAuth2PasswordBearer,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)

from passlib.context import CryptContext
from jose import jwt, JWTError
from bson import ObjectId

from .database import users_collection
from .models import UserCreate, UserLogin


# ---------------- CONFIG ----------------

SECRET_KEY = os.getenv("JWT_SECRET", "dev_secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 1

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
security = HTTPBearer()


# ---------------- PASSWORD UTILS ----------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------- JWT UTILS ----------------

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload["sub"]

        user = await users_collection.find_one({"_id": ObjectId(user_id)})

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User no longer exists"
            )

        return user_id

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def authenticate_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # contains sub + email
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


# ---------------- AUTH CONTROLLERS ----------------

async def register_user_controller(user: UserCreate):
    # check if user already exists
    if await users_collection.find_one({"email": user.email}):
        raise HTTPException(
            status_code=409,
            detail="Email already registered.",
        )

    user_dict = {
        "name": user.name,
        "email": user.email,
        "password": hash_password(user.password),
    }

    result = await users_collection.insert_one(user_dict)

    token = create_access_token(
        {
            "sub": str(result.inserted_id),
            "email": user.email,
        }
    )

    return {"token": token}


async def login_user_controller(credentials: UserLogin):
    user = await users_collection.find_one({"email": credentials.email})

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials.",
        )

    if not verify_password(credentials.password, user["password"]):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials.",
        )

    token = create_access_token(
        {
            "sub": str(user["_id"]),
            "email": user["email"],
        }
    )

    return {"token": token}