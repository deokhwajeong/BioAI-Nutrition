"""Accounts: hashing, tokens, per-user isolation, consent, and real deletion."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.biomarkers.base import BiomarkerReading as Reading
from app.biomarkers.base import BiomarkerType
from app.main import app, settings
from app.models.database import (
    Account,
    AuthToken,
    Base,
    BiomarkerReading,
    DailyLog,
    Event,
    User,
    get_db,
)
from app.privacy.consent_manager import ConsentScope
from app.routers import biomarker_engine as eng
from app.services.accounts import hash_password, verify_password

API = {"X-API-Key": settings.api_key}


@pytest.fixture()
def db_session() -> Iterator[sessionmaker]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False)

    def override() -> Iterator:
        db = Session()
        try:
            yield db
        finally:
            db.close()

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    yield Session
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


@pytest.fixture()
def client(db_session) -> TestClient:
    return TestClient(app)


def signup(client: TestClient, username: str, password: str = "correct horse") -> dict:
    res = client.post(
        "/auth/register", headers=API, json={"username": username, "password": password}
    )
    assert res.status_code == 201, res.text
    login = client.post(
        "/auth/login", headers=API, json={"username": username, "password": password}
    )
    assert login.status_code == 200, login.text
    body = login.json()
    return {"id": body["user_id"], "h": {**API, "Authorization": f"Bearer {body['access_token']}"}}


def test_password_hash_is_salted_and_verifies() -> None:
    a, b = hash_password("s3cret-pass"), hash_password("s3cret-pass")
    assert a != b and a.startswith("scrypt$")
    assert verify_password("s3cret-pass", a)
    assert not verify_password("wrong-pass", a)
    assert not verify_password("s3cret-pass", "plain-text")


def test_register_login_me_and_logout(client: TestClient, db_session) -> None:
    user = signup(client, "ana")
    me = client.get("/users/me", headers=user["h"])
    assert me.status_code == 200
    assert me.json()["username"] == "ana" and me.json()["user_id"] == user["id"]

    with db_session() as db:
        stored = db.get(Account, user["id"])
        assert "correct horse" not in stored.password_hash
        token = user["h"]["Authorization"].split()[1]
        assert all(token not in t.token_hash for t in db.query(AuthToken).all())

    assert client.post("/auth/logout", headers=user["h"]).status_code == 204
    assert client.get("/users/me", headers=user["h"]).status_code == 401


def test_auth_failures(client: TestClient) -> None:
    signup(client, "ben")
    dup = client.post(
        "/auth/register", headers=API, json={"username": "ben", "password": "another pw"}
    )
    assert dup.status_code == 409
    wrong = client.post(
        "/auth/login", headers=API, json={"username": "ben", "password": "nope-nope"}
    )
    unknown = client.post(
        "/auth/login", headers=API, json={"username": "zed", "password": "nope-nope"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # no username probing
    assert client.get("/users/me", headers=API).status_code == 401
    bad = {**API, "Authorization": "Bearer not-a-token"}
    assert client.get("/users/me", headers=bad).status_code == 401
    short = client.post("/auth/register", headers=API, json={"username": "cy", "password": "short"})
    assert short.status_code == 422
    # The API key is still required in front of everything.
    assert (
        client.post("/auth/login", json={"username": "ben", "password": "x" * 8}).status_code == 401
    )


def test_expired_token_is_rejected(client: TestClient, db_session) -> None:
    user = signup(client, "dee")
    with db_session() as db:
        for t in db.query(AuthToken).all():
            t.expires_at = datetime(2000, 1, 1)
        db.commit()
    assert client.get("/users/me", headers=user["h"]).status_code == 401


def test_profiles_consent_and_logs_are_isolated(client: TestClient) -> None:
    a, b = signup(client, "alice"), signup(client, "bob")
    client.put("/users/me/profile", headers=a["h"], json={"weight_kg": 61, "sex": "female"})
    client.put("/users/me/consent", headers=a["h"], json={"scope": "glucose_data", "granted": True})
    client.put("/users/me/days", headers=a["h"], json={"date": "2026-06-01", "calories": 2100})

    assert client.get("/users/me", headers=b["h"]).json()["profile"]["weight_kg"] is None
    assert client.get("/users/me/consent", headers=b["h"]).json()["scopes"] == {}
    assert client.get("/users/me/days", headers=b["h"]).json() == []
    assert client.get("/users/me/analytics", headers=b["h"]).json()["days"] == 0

    assert client.get("/users/me", headers=a["h"]).json()["profile"]["weight_kg"] == 61
    assert client.get("/users/me/consent", headers=a["h"]).json()["scopes"] == {
        "glucose_data": True
    }
    days = client.get("/users/me/days", headers=a["h"]).json()
    assert [d["calories"] for d in days] == [2100]

    # Bob cannot delete Alice.
    assert client.delete(f"/users/{a['id']}", headers=b["h"]).status_code == 403


def test_consent_reaches_the_engine_gate(client: TestClient) -> None:
    user = signup(client, "erin")
    client.put(
        "/users/me/consent", headers=user["h"], json={"scope": "glucose_data", "granted": True}
    )
    assert eng._consent_manager.check_consent(user["id"], ConsentScope.GLUCOSE_DATA)
    client.put(
        "/users/me/consent", headers=user["h"], json={"scope": "glucose_data", "granted": False}
    )
    assert not eng._consent_manager.check_consent(user["id"], ConsentScope.GLUCOSE_DATA)
    bad = client.put(
        "/users/me/consent", headers=user["h"], json={"scope": "nope", "granted": True}
    )
    assert bad.status_code == 422


def test_day_log_upserts_by_date_and_feeds_analytics(client: TestClient) -> None:
    user = signup(client, "finn")
    for i, kcal in enumerate([2500, 2400, 2300]):
        client.put(
            "/users/me/days",
            headers=user["h"],
            json={"date": f"2026-06-0{i + 1}", "calories": kcal},
        )
    client.put("/users/me/days", headers=user["h"], json={"date": "2026-06-03", "calories": 2000})
    days = client.get("/users/me/days", headers=user["h"]).json()
    assert [d["calories"] for d in days] == [2500, 2400, 2000]
    trends = client.get("/users/me/analytics", headers=user["h"]).json()
    energy = next(m for m in trends["metrics"] if m["key"] == "calories")
    assert energy["logged_days"] == 3 and energy["slope_per_week"] < 0


def test_delete_erases_rows_and_engine_state(client: TestClient, db_session) -> None:
    keep, gone = signup(client, "keeper"), signup(client, "leaver")
    uid = gone["id"]
    for user in (keep, gone):
        client.put("/users/me/days", headers=user["h"], json={"date": "2026-06-01", "steps": 5000})
        client.put(
            "/users/me/consent", headers=user["h"], json={"scope": "glucose_data", "granted": True}
        )
    with db_session() as db:
        db.add(User(id=uid))
        db.add(Event(user_id=uid, event_type="diet", calories=500))
        db.add(
            BiomarkerReading(
                source_id="cgm",
                user_id=uid,
                biomarker_type="glucose",
                timestamp=datetime(2026, 6, 1),
                value=100.0,
            )
        )
        db.commit()
    import asyncio

    pushed = asyncio.run(
        eng._cgm_adapter.push_reading(
            Reading(
                source_id="cgm-dexcom-g7",
                user_id=uid,
                biomarker_type=BiomarkerType.GLUCOSE,
                timestamp=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5),
                value=101.0,
                unit="mg/dL",
            )
        )
    )
    assert pushed
    eng._privacy_engine.get_or_create_budget(uid)
    assert f"{uid}:glucose" in eng._cgm_adapter._readings_store

    res = client.delete(f"/users/{uid}", headers=gone["h"])
    assert res.status_code == 200, res.text
    report = res.json()
    assert report["deleted"]["daily_logs"] == 1 and report["deleted"]["events"] == 1
    assert report["deleted"]["biomarker_readings"] == 1 and report["deleted"]["tokens"] == 1

    with db_session() as db:
        assert db.get(Account, uid) is None
        assert db.query(DailyLog).filter(DailyLog.account_id == uid).count() == 0
        assert db.query(AuthToken).filter(AuthToken.account_id == uid).count() == 0
        assert db.query(Event).filter(Event.user_id == uid).count() == 0
        assert db.query(User).filter(User.id == uid).count() == 0
        assert db.query(DailyLog).filter(DailyLog.account_id == keep["id"]).count() == 1

    assert f"{uid}:glucose" not in eng._cgm_adapter._readings_store
    assert uid not in eng._consent_manager._states
    assert all(r.user_id != uid for r in eng._consent_manager._audit_log)
    assert uid not in eng._privacy_engine._budgets
    assert eng._consent_manager.check_consent(keep["id"], ConsentScope.GLUCOSE_DATA)

    assert client.get("/users/me", headers=gone["h"]).status_code == 401
    assert client.get("/users/me", headers=keep["h"]).status_code == 200
