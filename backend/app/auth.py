from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from fastapi import Depends

TEST_USER_EMAIL = "test@example.com"


def get_current_user(db: Session = Depends(get_db)) -> models.User:
    """Temporary stand-in for real auth (added in Phase 3).

    Always returns the same test user, creating it with the starting
    $10,000 balance the first time it's needed.
    """
    user = db.query(models.User).filter(models.User.email == TEST_USER_EMAIL).first()
    if user is None:
        user = models.User(
            email=TEST_USER_EMAIL,
            password_hash="not-a-real-hash",
            cash_balance=10000.00,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
