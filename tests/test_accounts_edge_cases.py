"""Tests written from the spec and from what an attacker or careless client might do,
not from how the code currently works. A failure here may be a real bug in the app.
"""
import base64
import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from conftest import auth_headers, scale_ids, signup


def real_secret():
    from app.config import settings
    return settings.jwt_secret.get_secret_value()


def future():
    return datetime.now(timezone.utc) + timedelta(minutes=5)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def swap_payload(token, user_id):
    """Keep the signature but rewrite who the token claims to be."""
    header, _, signature = token.split(".")
    payload = base64.urlsafe_b64encode(json.dumps({"sub": str(user_id), "exp": 9999999999}).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}.{signature}"


#each one takes (victim's id, a real token belonging to a different user) and returns request headers
FORGERIES = {
    "signed_with_wrong_secret": lambda uid, _: bearer(jwt.encode({"sub": str(uid), "exp": future()}, "y" * 40, algorithm="HS256")),
    "alg_none_unsigned": lambda uid, _: bearer(jwt.encode({"sub": str(uid), "exp": future()}, None, algorithm="none")),
    "expired": lambda uid, _: bearer(jwt.encode({"sub": str(uid), "exp": datetime.now(timezone.utc) - timedelta(seconds=5)}, real_secret(), algorithm="HS256")),
    "no_sub": lambda uid, _: bearer(jwt.encode({"exp": future()}, real_secret(), algorithm="HS256")),
    "non_numeric_sub": lambda uid, _: bearer(jwt.encode({"sub": "abc", "exp": future()}, real_secret(), algorithm="HS256")),
    "user_does_not_exist": lambda uid, _: bearer(jwt.encode({"sub": "999999", "exp": future()}, real_secret(), algorithm="HS256")),
    "payload_swapped_to_victim": lambda uid, other: bearer(swap_payload(other, uid)),
    "wrong_scheme": lambda uid, other: {"Authorization": f"Basic {other}"},
}


@pytest.mark.parametrize("forgery", FORGERIES, ids=str)
def test_forged_tokens_are_rejected(api, forgery):
    victim = signup(api, "teacher")
    attacker = signup(api, "student")
    attacker_token = auth_headers(api, attacker["username"])["Authorization"].split()[1]

    #control: a correctly signed token for the victim does work, so a 401 below is about the forgery
    genuine = jwt.encode({"sub": str(victim["id"]), "exp": future()}, real_secret(), algorithm="HS256")
    assert api.get("/auth/me", headers=bearer(genuine)).status_code == 200

    r = api.get("/auth/me", headers=FORGERIES[forgery](victim["id"], attacker_token))
    assert r.status_code == 401


def test_students_only_see_their_own_assignments(api):
    t1 = signup(api, "teacher", name="Teacher One")
    t2 = signup(api, "teacher", name="Teacher Two")
    s1 = signup(api, "student")
    s2 = signup(api, "student")
    h1, h2 = auth_headers(api, t1["username"]), auth_headers(api, t2["username"])
    scales = scale_ids(api, h1)
    g, a = scales["G Major"], scales["A Major"]

    def send(headers, student, ids):
        r = api.post("/assignments", json={"student_username": student["username"], "scale_ids": ids}, headers=headers)
        assert r.status_code == 201
        return r.json()

    send(h1, s1, [g])
    #uniqueness includes the teacher, so a second teacher assigning G is new, not a duplicate
    assert len(send(h2, s1, [g])) == 1
    send(h1, s2, [a])

    first = api.get("/assignments/me", headers=auth_headers(api, s1["username"])).json()
    second = api.get("/assignments/me", headers=auth_headers(api, s2["username"])).json()

    assert sorted((x["scale"]["name"], x["teacher"]["name"]) for x in first) == [
        ("G Major", "Teacher One"),
        ("G Major", "Teacher Two"),
    ]
    assert [(x["scale"]["name"], x["teacher"]["name"]) for x in second] == [("A Major", "Teacher One")]
    #a student sees the teacher's display name and nothing else about the account
    assert set(first[0]["teacher"]) == {"id", "name"}


def test_role_change_and_deletion_apply_to_tokens_already_issued(api):
    from sqlalchemy import delete, update
    from app.db import SessionLocal
    from app.models import User

    teacher = signup(api, "teacher")
    student = signup(api, "student")
    teacher_headers = auth_headers(api, teacher["username"])
    student_headers = auth_headers(api, student["username"])
    scale = scale_ids(api, teacher_headers)["G Major"]
    body = {"student_username": student["username"], "scale_ids": [scale]}
    assert api.post("/assignments", json=body, headers=teacher_headers).status_code == 201

    #demoted: the same token immediately loses teacher access and gains student access
    with SessionLocal() as db:
        db.execute(update(User).where(User.id == teacher["id"]).values(role="student"))
        db.commit()
    assert api.post("/assignments", json=body, headers=teacher_headers).status_code == 403
    assert api.get("/assignments/me", headers=teacher_headers).status_code == 200

    #deleted: the same token stops working, and that teacher's assignments go with them
    with SessionLocal() as db:
        db.execute(delete(User).where(User.id == teacher["id"]))
        db.commit()
    assert api.get("/auth/me", headers=teacher_headers).status_code == 401
    assert api.get("/scales", headers=teacher_headers).status_code == 401
    assert api.get("/assignments/me", headers=student_headers).json() == []


@pytest.mark.parametrize(
    "bad_id",
    [0, -1, 2**31, 2**63, 10**30, -(2**31) - 1],
    ids=["zero", "negative", "over_int4", "over_int8", "huge", "under_int4"],
)
def test_any_scale_id_that_does_not_exist_is_a_400_and_saves_nothing(api, bad_id):
    teacher = signup(api, "teacher")
    student = signup(api, "student")
    headers = auth_headers(api, teacher["username"])
    good_id = scale_ids(api, headers)["G Major"]

    r = api.post(
        "/assignments",
        json={"student_username": student["username"], "scale_ids": [good_id, bad_id]},
        headers=headers,
    )
    assert r.status_code == 400
    assert r.json()["detail"] == f"Unknown scale ids: {[bad_id]}"
    assert api.get("/assignments/me", headers=auth_headers(api, student["username"])).json() == []


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("name", "a\x00b", 422),                #Postgres text can't store a NUL byte
        ("name", "   ", 422),                   #blank once stripped
        ("name", "n" * 101, 422),
        ("username", "  ab  ", 422),            #only 2 characters once stripped
        ("username", "x' OR '1'='1", 422),
        ("username", "álex", 422),
        ("password", "short12", 422),           #7 characters
        ("password", "é" * 37, 422),            #37 characters, but 74 bytes: too long for bcrypt
        ("password", "é" * 36, 201),            #exactly 72 bytes: the longest allowed
    ],
    ids=["nul_in_name", "blank_name", "long_name", "short_username", "sql_username", "accented_username", "short_password", "password_73_plus_bytes", "password_72_bytes"],
)
def test_signup_input_limits(api, field, value, expected):
    body = {"name": "Test", "username": "valid_name", "password": "password123", "role": "student"}
    body[field] = value

    r = api.post("/auth/signup", json=body)
    assert r.status_code == expected

    if expected == 201:
        #an accepted password must also log in, and only when it matches exactly
        assert api.post("/auth/login", json={"username": body["username"], "password": value}).status_code == 200
        assert api.post("/auth/login", json={"username": body["username"], "password": "é" * 35 + "e"}).status_code == 401
