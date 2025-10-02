import json
from datetime import datetime, timedelta
from app.models import db
from app.models.user import User
from tests.helpers import create_student


def _api_login(client, email, password):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return resp


def test_auth_lockout_flow(client, app_context):
    # Ensure student exists with known password
    user = create_student("lockout@test.edu")

    # 5 failed attempts
    for _ in range(5):
        r = _api_login(client, user.email, "wrongpass")
        assert r.status_code == 401

    # Now even with correct password, should be locked out
    r = _api_login(client, user.email, "pass12345")
    assert r.status_code == 401

    # Manually expire lock and try again
    u = User.query.filter_by(email=user.email).first()
    assert u is not None
    u.locked_until = datetime.utcnow() - timedelta(minutes=1)
    db.session.commit()

    r = _api_login(client, user.email, "pass12345")
    assert r.status_code == 200
    data = r.get_json()
    assert "access_token" in data
