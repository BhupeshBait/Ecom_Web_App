import re
import uuid
from io import BytesIO
from pathlib import Path
# authentication helpers are provided by core.security
import bcrypt
from email_validator import EmailNotValidError, validate_email
from fastapi import Depends, Header, HTTPException, UploadFile
from PIL import Image, ImageOps
from sqlalchemy import and_, or_

from database.database import local_session
from models.models import Users


cover_dir = Path("uploads/cover")
hero_dir = Path("uploads/hero")


def getdb():
    db = local_session()
    try:
        yield db
    finally:
        db.close()


def basic_validate(email):
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if bool(re.fullmatch(email_pattern, email)):
        return email


def adv_validation(email: str):
    try:
        if basic_validate(email):
            email_val = basic_validate(email)
            emailinfo = validate_email(email_val, check_deliverability=False)
            return emailinfo.normalized
        return False
    except EmailNotValidError as e:
        return False


def check_user_exists(email: str | None,
                      username: str | None, db):
    user = (
        db.query(Users)
        .filter(or_(Users.email == email, Users.user_name == username))
        .first()
    )

    if user:
        if user.email == email:
            return "Email already registered!"
        if user.user_name == username:
            return "Username already taken!"
    return None




def name_validation(name):
    name_pattern = r"[a-zA-Z]"
    if bool(re.match(name_pattern, name)):
        return True
    return False


def validate_contact(contact: str) -> bool:
    contact_no = contact.removeprefix("+91")
    if contact_no.isnumeric() and len(contact_no) == 10:
        return True
    return False


def validate_username(username: str) -> bool:
    u_pattern = r"^[a-zA-Z][a-zA-Z0-9_]{2,15}$"
    if not re.match(u_pattern, username):
        return False
    return True


def complete_registration(
    email: str, username: str, contact: str, first_name: str, last_name: str, db
) -> str:
    if not name_validation(first_name):
        return "Enter a valid first name!"

    if not name_validation(last_name):
        return "Enter a valid Last name!"

    if not validate_username(username):
        return "Username must be 3-15 characters, start with a letter, and use only letters, numbers, or underscores."

    if not validate_contact(contact):
        return "Enter a valid Contact number!"

    if not adv_validation(email):
        return "Enter a valid email!"


    user_check = check_user_exists(email, username, db)
    if user_check:
        return user_check

    return "Done"




def process_images(content: bytes, type: str | None = None) -> dict:
    try:
        with Image.open(BytesIO(content)) as original:
            img = ImageOps.exif_transpose(original)
            
            if type == "hero":
                img = ImageOps.fit(
                    img, (1280, 720), method=Image.Resampling.LANCZOS)
            else:
                img = ImageOps.fit(
                    img, (1024, 600), method=Image.Resampling.LANCZOS)
                
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            filename = f"{uuid.uuid4().hex}.jpg"
            
            if type == "hero":
                filepath = hero_dir / filename
            else:
                filepath = cover_dir / filename

            if type == "hero":
                hero_dir.mkdir(parents=True, exist_ok=True)
            else:
                cover_dir.mkdir(parents=True, exist_ok=True)

            img.save(filepath, "JPEG", quality=90, optimize=True)
            
            return {
                "FileName": filename, 
                "FilePath": str(filepath)  
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Image processing failed: {str(e)}"
        )



ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 8 * 1024 * 1024  
MIN_FILE_SIZE = 10 * 1024  
MAX_IMAGE_WIDTH = 10000  
MAX_IMAGE_HEIGHT = 10000  
MIN_IMAGE_WIDTH = 100  
MIN_IMAGE_HEIGHT = 100  


def sanitize_filename(filename: str) -> str:
    filename = Path(filename).name
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    if len(filename) > 255:
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:250] + ext
    
    return filename


def validate_image_file(file: UploadFile):
    if file is None:
        return

    if not file.filename:
        raise HTTPException(
            status_code=400, 
            detail="Filename is required"
        )

    filename = file.filename.lower().strip()
    file_ext = Path(filename).suffix.lower()
    
    if not file_ext:
        raise HTTPException(
            status_code=400, 
            detail=f"File '{file.filename}' has no extension. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Extension '{file_ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"File type '{file.content_type}' not supported. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    if file.size:
        if file.size > MAX_FILE_SIZE:
            size_mb = MAX_FILE_SIZE / (1024 * 1024)
            raise HTTPException(
                status_code=400, 
                detail=f"File size ({file.size / (1024*1024):.1f}MB) exceeds maximum allowed size of {size_mb:.0f}MB"
            )
        
        if file.size < MIN_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File size ({file.size / 1024:.1f}KB) is too small. Minimum: {MIN_FILE_SIZE / 1024:.0f}KB"
            )

    try:
        file.file.seek(0)  
        image_content = file.file.read()
        
        with Image.open(BytesIO(image_content)) as img:
            width, height = img.size
            
            if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Image dimensions ({width}x{height}px) too small. Minimum: {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT}px"
                )
            
            if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Image dimensions ({width}x{height}px) too large. Maximum: {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT}px"
                )
            
            img_format = img.format.lower() if img.format else None
            if img_format not in ["jpeg", "png", "webp"]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Image format '{img_format}' not supported. Supported: JPEG, PNG, WebP"
                )
        
        file.file.seek(0)  
        
    except Exception as e:
        if "Image" in str(type(e)):
            raise HTTPException(
                status_code=400, 
                detail=f"File '{file.filename}' is not a valid image file"
            )
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=400, 
            detail=f"Image validation failed: {str(e)}"
        )





from core.security import (
    getdb as _getdb,
    get_token_from_header,
    get_current_user,
    hash_passwd,
    verify_password_hash,
    create_access_token,
    create_refresh_token,
    require_admin,
    require_customer,
)

getdb = _getdb

hash_passwd = hash_passwd
verify_password = verify_password_hash
create_access_token = create_access_token
create_refresh_token = create_refresh_token
