from datetime import datetime, timedelta, timezone
import jwt

from app.config import Settings


def create_tokens(email: str, user_id: int, name: str):
    access_token = jwt.encode(
        {'user_id': user_id, 'email': email, 'name': name, 'exp': datetime.now(timezone.utc) + timedelta(minutes=int(Settings.ACCESS_TOKEN_EXPIRE_MINUTES))},
        Settings.JWT_SECRET,
        algorithm=Settings.JWT_ALGORITHM
    )

    refresh_token = jwt.encode(
        {'user_id': user_id, 'email': email, 'exp': datetime.now(timezone.utc) + timedelta(minutes=int(Settings.ACCESS_TOKEN_EXPIRE_MINUTES))},
        Settings.JWT_SECRET,
        algorithm=Settings.JWT_ALGORITHM
    )

    return access_token, refresh_token