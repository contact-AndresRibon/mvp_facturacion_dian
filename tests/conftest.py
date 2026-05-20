import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ALLOW_PUBLIC_REGISTER"] = "true"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session", scope="function")
def session_fixture() -> Generator[Session, None, None]:
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "legal_name": "Empresa Demo SAS",
            "nit": "900123456",
            "dv": "1",
            "email": "empresa@demo.com",
            "admin_email": "admin@demo.com",
            "admin_password": "secret1234",
            "admin_full_name": "Admin Demo",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
