import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from api.deps import get_session
from api.main import app

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
        "paths": ["file1.hdf5", "file2.hdf5"],
    }


@pytest.fixture(scope="session", autouse=True)
def cleanup_database():
    yield
    import os

    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture
def invalid_extension_project():
    return {
        "name": "Invalid Extension Project",
        "favourite": False,
        "description": "Project with invalid file extensions",
        "paths": ["file1.txt", "file2.csv", "file3.hdf5"],
    }


@pytest.fixture
def mixed_file_types_project():
    return {
        "name": "Mixed File Types Project",
        "favourite": False,
        "description": "Project with mixed file types",
        "paths": ["file1.hdf5", "file2.fits"],
    }


@pytest.fixture
def valid_hdf5_project():
    return {
        "name": "Valid HDF5 Project",
        "favourite": True,
        "description": "Project with only HDF5 files",
        "paths": ["file1.hdf5", "file2.hdf5"],
    }


@pytest.fixture
def valid_fits_project():
    return {
        "name": "Valid FITS Project",
        "favourite": True,
        "description": "Project with only FITS files",
        "paths": ["file1.fits", "file2.fits"],
    }
