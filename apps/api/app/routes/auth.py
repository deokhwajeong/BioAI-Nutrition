"""Registration, login, and logout with opaque bearer tokens."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..models.database import Account, get_db
from ..schemas.accounts import AccountOut, Credentials, Profile, TokenOut
from ..services.accounts import (
    account_for_token,
    hash_password,
    issue_token,
    new_account_id,
    revoke_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

bearer = HTTPBearer(auto_error=False)


def current_token(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return creds.credentials


def current_account(token: str = Depends(current_token), db: Session = Depends(get_db)) -> Account:
    """Resolve the bearer token to an account, or 401."""
    account = account_for_token(db, token)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return account


def account_out(account: Account) -> AccountOut:
    return AccountOut(
        user_id=account.id,
        username=account.username,
        created_at=account.created_at,
        profile=Profile(
            weight_kg=account.weight_kg,
            height_cm=account.height_cm,
            age=account.age,
            sex=account.sex,
            activity_level=account.activity_level,
        ),
    )


@router.post("/register", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def register(creds: Credentials, db: Session = Depends(get_db)) -> AccountOut:
    if db.query(Account).filter(Account.username == creds.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username taken")
    account = Account(
        id=new_account_id(),
        username=creds.username,
        password_hash=hash_password(creds.password),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account_out(account)


@router.post("/login", response_model=TokenOut)
def login(creds: Credentials, db: Session = Depends(get_db)) -> TokenOut:
    account = db.query(Account).filter(Account.username == creds.username).first()
    # Same error for unknown user and wrong password, so usernames cannot be probed.
    if account is None or not verify_password(creds.password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong username or password"
        )
    token, expires_at = issue_token(db, account)
    return TokenOut(access_token=token, expires_at=expires_at, user_id=account.id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: str = Depends(current_token), db: Session = Depends(get_db)) -> None:
    revoke_token(db, token)
