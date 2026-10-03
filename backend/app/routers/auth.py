from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import create_access_token, current_user, verify_credentials

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    if not verify_credentials(payload.username, payload.password):
        raise HTTPException(401, "اسم المستخدم أو كلمة المرور غير صحيحة")
    token = create_access_token(payload.username)
    return TokenResponse(access_token=token, username=payload.username)


@router.get("/me")
def me(username: str = Depends(current_user)):
    return {"username": username}
