from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from jwt import InvalidTokenError

from app.config import settings

REFRESH_TOKEN_EXPIRE_DAYS = 14


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    if not senha_hash:
        return False
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def criar_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({"type": "access"})
    # Claims vão para JSON: usar timestamp numérico em exp (datetime quebra o encode).
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def criar_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({"type": "refresh"})
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") not in (None, "access"):
            return None
        return payload
    except InvalidTokenError:
        return None


def decodificar_refresh_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except InvalidTokenError:
        return None
