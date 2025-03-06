import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.db import get_session
from sqlmodel import Session, SQLModel, create_engine

TEST_DATABASE_URL = "sqlite:///test.db"


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def new_project():
    return {
        "name": "Test Project",
        "favourite": True,
        "description": "A test project",
        "paths": ["file1", "file2"],
    }


@pytest.fixture(scope="session", autouse=True)
def cleanup_database():
    yield
    import os

    if os.path.exists("test.db"):
        os.remove("test.db")
