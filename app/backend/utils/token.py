from datetime import datetime, time, timedelta
from functools import wraps

import jwt

SECRET_KEY = "Bhup123@133"
algorithm = "HS256"


def create_token(username, email):
    userinfo = username + "+" + email
    jwtobj = {
        "iss": "Tech_comm",
        "sub": userinfo,
        "exp": datetime.now() + timedelta(minutes=30),
        "iat": int(datetime.now().timestamp()),
    }

    token = jwt.encode(jwtobj, SECRET_KEY, algorithm=algorithm)
    return token


def verify_token(token):
    decode_obj = jwt.decode(token, SECRET_KEY, algorithms=algorithm)
    return decode_obj
