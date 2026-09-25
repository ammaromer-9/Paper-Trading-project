from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import create_access_token, hash_password, verify_password
from app.database import get_db

router = APIRouter()


@router.post("/signup", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def signup(body: schemas.SignupRequest, db: Session = Depends(get_db)):
    email = body.email.lower()

    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = models.User(
        email=email,
        password_hash=hash_password(body.password),
        cash_balance=10000.00,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm names the field "username"; we treat it as the email.
    email = form_data.username.lower()
    user = db.query(models.User).filter(models.User.email == email).first()

    invalid_credentials = HTTPException(status_code=401, detail="Invalid email or password")
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise invalid_credentials

    token = create_access_token(user.id)
    return schemas.TokenResponse(access_token=token)
