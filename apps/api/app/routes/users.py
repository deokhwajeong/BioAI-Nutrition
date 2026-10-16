"""Per-user endpoints: profile, consent, logged days, analytics, and deletion.

Every route here acts on the account behind the bearer token. A token only ever reaches its
own account: there is no user_id in these paths except DELETE /users/{user_id}, which must
match the token's account.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..models.database import Account, AccountConsent, DailyLog, get_db
from ..privacy.consent_manager import ConsentScope
from ..routers.biomarker_engine import _consent_manager, purge_user_state
from ..schemas.accounts import (
    AccountConsentOut,
    AccountOut,
    ConsentUpdate,
    DeletionReport,
    Profile,
)
from ..schemas.analytics import LoggedDay, TrendsResponse
from ..services.accounts import delete_account_data
from ..services.analytics import compute_trends
from .auth import account_out, current_account

router = APIRouter()

_LOG_FIELDS = tuple(f for f in LoggedDay.model_fields if f != "date")


@router.get("/me", response_model=AccountOut)
def me(account: Account = Depends(current_account)) -> AccountOut:
    return account_out(account)


@router.put("/me/profile", response_model=AccountOut)
def update_profile(
    profile: Profile,
    account: Account = Depends(current_account),
    db: Session = Depends(get_db),
) -> AccountOut:
    for field, value in profile.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account_out(account)


def _consent_out(account: Account) -> AccountConsentOut:
    return AccountConsentOut(
        user_id=account.id, scopes={c.scope: c.granted for c in account.consents}
    )


@router.get("/me/consent", response_model=AccountConsentOut)
def get_consent(account: Account = Depends(current_account)) -> AccountConsentOut:
    return _consent_out(account)


@router.put("/me/consent", response_model=AccountConsentOut)
def set_consent(
    update: ConsentUpdate,
    account: Account = Depends(current_account),
    db: Session = Depends(get_db),
) -> AccountConsentOut:
    """Store the decision and apply it to the engine's consent gate for this user id."""
    scope = update.scope.value
    row = next((c for c in account.consents if c.scope == scope), None)
    if row is None:
        account.consents.append(AccountConsent(scope=scope, granted=update.granted))
    else:
        row.granted = update.granted
    db.commit()
    db.refresh(account)
    if update.granted:
        _consent_manager.grant_consent(account.id, ConsentScope(scope), "account setting")
    else:
        _consent_manager.revoke_consent(account.id, ConsentScope(scope), "account setting")
    return _consent_out(account)


@router.put("/me/days", response_model=LoggedDay)
def log_day(
    day: LoggedDay,
    account: Account = Depends(current_account),
    db: Session = Depends(get_db),
) -> LoggedDay:
    """Create or replace the log for one date."""
    row = next((d for d in account.daily_logs if d.date == day.date), None)
    if row is None:
        row = DailyLog(date=day.date)
        account.daily_logs.append(row)
    for field in _LOG_FIELDS:
        setattr(row, field, getattr(day, field))
    db.commit()
    return day


def _logged_days(account: Account) -> list[LoggedDay]:
    return [
        LoggedDay(date=d.date, **{f: getattr(d, f) for f in _LOG_FIELDS})
        for d in sorted(account.daily_logs, key=lambda d: d.date)
    ]


@router.get("/me/days", response_model=list[LoggedDay])
def list_days(account: Account = Depends(current_account)) -> list[LoggedDay]:
    return _logged_days(account)


@router.get("/me/analytics", response_model=TrendsResponse)
def my_analytics(account: Account = Depends(current_account)) -> TrendsResponse:
    days = [d.model_dump(exclude_none=True) for d in _logged_days(account)]
    return TrendsResponse(**compute_trends(days))


@router.delete("/{user_id}", response_model=DeletionReport)
def delete_user(
    user_id: str,
    account: Account = Depends(current_account),
    db: Session = Depends(get_db),
) -> DeletionReport:
    """Erase the account and all of its data: stored rows and in-process engine state.

    Only the account itself may do this. Tokens stop working immediately.
    """
    if user_id != account.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own account"
        )
    counts = delete_account_data(db, account, purge_runtime=purge_user_state)
    return DeletionReport(user_id=user_id, deleted=counts)
