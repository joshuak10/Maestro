from conftest import auth_headers, scale_ids, signup


def setup_teacher_and_student(api):
    teacher = signup(api, "teacher", name="Kim")
    student = signup(api, "student")
    headers = auth_headers(api, teacher["username"])
    return headers, student, scale_ids(api, headers)


def assign(api, headers, username, ids):
    return api.post("/assignments", json={"student_username": username, "scale_ids": ids}, headers=headers)


def test_assigning_only_returns_new_rows(api):
    headers, student, scales = setup_teacher_and_student(api)
    g, d, a = scales["G Major"], scales["D Major"], scales["A Major"]

    first = assign(api, headers, student["username"], [g, d])
    assert first.status_code == 201
    assert [x["scale_id"] for x in first.json()] == [g, d]

    resend = assign(api, headers, student["username"], [g, d])
    assert resend.status_code == 201
    assert resend.json() == []

    partly_new = assign(api, headers, student["username"], [g, a])
    assert partly_new.status_code == 201
    assert [x["scale_id"] for x in partly_new.json()] == [a]


def test_student_cannot_assign(api):
    _, student, scales = setup_teacher_and_student(api)
    headers = auth_headers(api, student["username"])
    r = assign(api, headers, student["username"], [scales["G Major"]])
    assert r.status_code == 403


def test_teacher_username_is_rejected(api):
    headers, _, scales = setup_teacher_and_student(api)
    other_teacher = signup(api, "teacher")
    r = assign(api, headers, other_teacher["username"], [scales["G Major"]])
    assert r.status_code == 400
    assert r.json()["detail"] == "No student with that username"


def test_unknown_scale_is_rejected(api):
    headers, student, _ = setup_teacher_and_student(api)
    r = assign(api, headers, student["username"], [99])
    assert r.status_code == 400
    assert r.json()["detail"] == "Unknown scale ids: [99]"


def test_my_assignments_has_names_and_newest_first(api):
    headers, student, scales = setup_teacher_and_student(api)
    assign(api, headers, student["username"], [scales["G Major"]])
    #sent together, so these two share a created_at and id breaks the tie
    assign(api, headers, student["username"], [scales["D Major"], scales["A Major"]])

    r = api.get("/assignments/me", headers=auth_headers(api, student["username"]))
    assert r.status_code == 200
    assert [x["scale"]["name"] for x in r.json()] == ["A Major", "D Major", "G Major"]
    assert {x["teacher"]["name"] for x in r.json()} == {"Kim"}


def test_teacher_cannot_read_student_list(api):
    headers, _, _ = setup_teacher_and_student(api)
    assert api.get("/assignments/me", headers=headers).status_code == 403


def test_new_student_has_no_assignments(api):
    student = signup(api, "student")
    r = api.get("/assignments/me", headers=auth_headers(api, student["username"]))
    assert r.status_code == 200
    assert r.json() == []
