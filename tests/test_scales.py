from conftest import auth_headers, signup


def test_scales_with_token(api):
    user = signup(api, "student")
    r = api.get("/scales", headers=auth_headers(api, user["username"]))
    assert r.status_code == 200
    assert [s["name"] for s in r.json()] == ["G Major", "D Major", "A Major", "E Major"]


def test_scales_without_token(api):
    assert api.get("/scales").status_code == 401
