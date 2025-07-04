from fastapi.testclient import TestClient


class TestCreateProject:
    """Test project creation scenarios"""

    def test_create_project_hdf5(self, client: TestClient, valid_hdf5_project: dict):
        """Test creating project with only HDF5 files"""
        response = client.post("/api/projects/", json=valid_hdf5_project)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Valid HDF5 Project"
        assert data["paths"] == ["file1.hdf5", "file2.hdf5"]

    def test_create_project_fits(self, client: TestClient, valid_fits_project: dict):
        """Test creating project with only FITS files"""
        response = client.post("/api/projects/", json=valid_fits_project)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Valid FITS Project"
        assert data["paths"] == ["file1.fits", "file2.fits"]

    def test_create_project_invalid_file_extensions(
        self, client: TestClient, invalid_extension_project: dict
    ):
        """Test creating project with invalid file extensions"""
        response = client.post("/api/projects/", json=invalid_extension_project)
        assert response.status_code == 422

        error_data = response.json()
        assert "error" in error_data
        assert error_data["error"]["code"] == "INVALID_FILE_EXTENSION"

    def test_create_project_mixed_file_types(
        self, client: TestClient, mixed_file_types_project: dict
    ):
        """Test creating project with mixed file types"""
        response = client.post("/api/projects/", json=mixed_file_types_project)
        assert response.status_code == 422

        error_data = response.json()
        assert "error" in error_data
        assert error_data["error"]["code"] == "MIXED_FILE_TYPES"


def test_read_projects(client: TestClient):
    response = client.get("/api/projects/")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 2


def test_read_project(client: TestClient):
    response = client.get("/api/projects/")
    data = response.json()
    project_id = data[0]["id"]
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["id"] == project_id


def test_update_project(client: TestClient):
    response = client.get("/api/projects/")
    data = response.json()
    project_id = data[0]["id"]
    update_data = {"name": "Updated Project", "paths": ["file3.fits", "file4.fits"]}
    response = client.put(f"/api/projects/{project_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Updated Project"
    assert set(data["paths"]) == set(["file3.fits", "file4.fits"])

    update_data = {"name": "Updated Project", "paths": ["invalid.txt", "another.csv"]}
    response = client.put(f"/api/projects/{project_id}", json=update_data)
    assert response.status_code == 422

    error_data = response.json()
    assert error_data["error"]["code"] == "INVALID_FILE_EXTENSION"


class TestUpdateProject:
    """Test project update scenarios"""

    def test_update_project_valid_data(self, client: TestClient):
        """Test updating project with valid data"""
        response = client.get("/api/projects/")
        data = response.json()
        if len(data) > 0:
            project_id = data[0]["id"]
            update_data = {
                "name": "Updated Project",
                "paths": ["file3.hdf5", "file4.hdf5"],
            }
            response = client.put(f"/api/projects/{project_id}", json=update_data)
            assert response.status_code == 200
            data = response.json()

            assert data["name"] == "Updated Project"
            assert set(data["paths"]) == set(["file3.hdf5", "file4.hdf5"])

    def test_update_project_invalid_file_extensions(self, client: TestClient):
        """Test updating project with invalid data"""
        response = client.get("/api/projects/")
        data = response.json()
        if len(data) > 0:
            project_id = data[0]["id"]
            update_data = {
                "name": "Updated Project",
                "paths": ["invalid.txt", "another.csv"],
            }
            response = client.put(f"/api/projects/{project_id}", json=update_data)
            assert response.status_code == 422

            error_data = response.json()
            assert error_data["error"]["code"] == "INVALID_FILE_EXTENSION"


def test_delete_project(client: TestClient):
    response = client.get("/api/projects/")
    data = response.json()
    project_id = data[0]["id"]
    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()

    assert data == {"message": "Project deleted successfully"}
