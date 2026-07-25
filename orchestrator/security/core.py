from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
import os
from orchestrator.config import get_settings

# Password hashing — bcrypt primary, pbkdf2_sha256 as deprecated fallback for auto-upgrade
pwd_context = CryptContext(schemes=["bcrypt", "pbkdf2_sha256"], deprecated="auto")
settings = get_settings()

# Load RS512 Keys
PRIVATE_KEY_PATH = "keys/private_key.pem"
PUBLIC_KEY_PATH = "keys/public_key.pem"

def load_keys():
    # Priority 1: Environment Variables (Production)
    private_key = os.getenv("RSA_PRIVATE_KEY")
    public_key = os.getenv("RSA_PUBLIC_KEY")
    
    if private_key and public_key:
        return private_key.replace("\\n", "\n"), public_key.replace("\\n", "\n")
        
    # Priority 2: Local Files (Development)
    try:
        if os.path.exists(PRIVATE_KEY_PATH):
            with open(PRIVATE_KEY_PATH, "r") as f:
                private_key = f.read()
        if os.path.exists(PUBLIC_KEY_PATH):
            with open(PUBLIC_KEY_PATH, "r") as f:
                public_key = f.read()
        
        if private_key and public_key:
            return private_key, public_key
    except Exception as e:
        print(f"Error loading keys from files: {e}")

    # Fallback/Error
    raise RuntimeError(
        "RSA keys not found! Please set RSA_PRIVATE_KEY/RSA_PUBLIC_KEY env vars "
        "or ensure keys/ exist locally."
    )

PRIVATE_KEY, PUBLIC_KEY = load_keys()
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None
