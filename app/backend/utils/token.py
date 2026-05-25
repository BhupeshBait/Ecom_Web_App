from datetime import datetime, time, timedelta, timezone
from functools import wraps

import jwt

SECRET_KEY = "Bhup123@133"
algorithm = "HS256"
TOKEN_EXPIRATION_MINUTES = 30


def create_token(username, email):
    userinfo = username + "+" + email
    jwtobj = {
        "iss": "Tech_comm",
        "sub": userinfo,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRATION_MINUTES),
        "iat": int(datetime.now().timestamp()),
    }

    token = jwt.encode(jwtobj, SECRET_KEY, algorithm=algorithm)
    return token


def verify_token(token):
    try:
        decode_obj = jwt.decode(token, SECRET_KEY, algorithms=[algorithm])
        return decode_obj
    except jwt.ExpiredSignatureError:
        raise jwt.InvalidTokenError("Token has expired")
    except jwt.InvalidTokenError:
        raise jwt.InvalidTokenError("Invalid token")
