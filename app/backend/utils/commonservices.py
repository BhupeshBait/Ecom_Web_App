from database.database import local_session
import re
from email_validator import validate_email,EmailNotValidError
import bcrypt
from models.models import Users
from sqlalchemy import or_
from PIL import Image,ImageOps
import uuid
from io import BytesIO
from pathlib import Path
from fastapi import HTTPException,UploadFile


cover_dir=Path("uploads/cover")
hero_dir=Path("uploads/hero")


def getdb():
    db=local_session()
    try:
        yield db
    finally:
        db.close()


def basic_validate(email):
    email_pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if bool(re.fullmatch(email_pattern,email)):
        return email
    
def adv_validation(email:str):
    try:
        if basic_validate(email):
            email_val=basic_validate(email)
            emailinfo=validate_email(email_val,check_deliverability=False)
            return emailinfo.normalized
        return False
    except EmailNotValidError as e:
        return False
        
def check_user_exists(email:str|NotImplementedError, username:str|None, db):
    user = db.query(Users).filter(
        or_(Users.email == email, Users.user_name == username)
    ).first()
    
    if user:
        if user.email == email:
            return "Email already registered!"
        if user.user_name == username:
            return "Username already taken!"
    return None

def hash_passwd(passwd):
    return bcrypt.hashpw(passwd.encode(),bcrypt.gensalt(rounds=12))

def name_validation(name):
    name_pattern=r"[a-zA-Z]"
    if bool(re.match(name_pattern,name)):
        return True
    return False

def validate_contact(contact:str)->bool:
    contact_no=contact.removeprefix("+91")
    if contact_no.isnumeric() and len(contact_no)==10:
        return True
    return False 

def validate_username(username:str)->bool:
    u_pattern=r'^[a-zA-Z][a-zA-Z0-9_]{2,15}$'
    if not re.match(u_pattern,username):
        return False
    return True

def complete_registration(email:str,username:str,contact:str,first_name:str,last_name:str,db)-> str:
    if not  name_validation(first_name):
        return "Enter a valid first name!"
    
    if not  name_validation(last_name):
        return "Enter a valid Last name!"
    
    if not  validate_username(username):
        return "Username must be 3-15 characters, start with a letter, and use only letters, numbers, or underscores."
    
    if not  validate_contact(contact):
        return "Enter a valid Contact number!"
    
    if not  adv_validation(email):
        return "Enter a valid email!"
    
    user = db.query(Users).filter(Users.user_name == username).first()

    if user is None:
        return {"Msg":"Incorrect Username or email"}
    user_check =  check_user_exists(email, username, db)
    if user_check:
        return user_check
    
    return "Done"

def verify_password(password:str,username:str,email:str,db):
    if check_user_exists(email,username,db)==None:
        return {'Msg':'Incoorect Username or email'}
    result= db.query(Users).filter(Users.user_name==username).first()
    

    if  result is None:
        return {"Msg":"Incorrect Username or email"}
    
    hash_passwd=bcrypt.checkpw(password.encode(),result.hash_password)
    if hash_passwd:
        return None
    return {"Msg":"Incorrect Password!"}




def process_images(content: bytes, type: str | None = None) -> dict:
    with Image.open(BytesIO(content)) as original:
        img=ImageOps.exif_transpose(original)
        if type=="hero":
             img = ImageOps.fit(img,(1280 ,720),method=Image.Resampling.LANCZOS)
        else:
             img = ImageOps.fit(img,(1024 ,600),method=Image.Resampling.LANCZOS)

        if img.mode in ("RGBA","LA","P"):
            img=img.convert("RGB")

        filename=f"{uuid.uuid4().hex}.jpg"
        if type=="hero":
            filepath=hero_dir/filename
        else:
            filepath=cover_dir/filename
        
        if type == "hero":
            hero_dir.mkdir(parents=True, exist_ok=True)
        else:
            cover_dir.mkdir(parents=True, exist_ok=True)

        img.save(filepath,"JPEG",quality=90,optimize=True)

    return {
        "FileName":filename,
        "FilePath":filepath
    }

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/jpg",
    "image/webp"
}

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}


def validate_image_file(file: UploadFile):
    if file is None:
        return

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"{file.filename} is not a valid image file"
        )

    filename = file.filename.lower()

    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"{file.filename} has invalid extension"
        )