from fastapi import HTTPException, status, Request
from .storages.tokens import Tokens
from secrets import token_urlsafe


async def check_token(request: Request):
    token = request.headers.get("Authorization")
    token = token.split(" ")[1] if token else None  # Bearer token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is missing"
        )
    if not token_exists(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    return token


def new_token():
    token = token_urlsafe(64)
    Tokens.add(token)
    return token


def remove_token(token: str):
    Tokens.delete(token)


def renew_token(token: str):
    Tokens.delete(token)
    return new_token()


def token_exists(token: str):
    return Tokens.exists(token)
