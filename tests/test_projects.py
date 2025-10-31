import pytest
from fastapi.testclient import TestClient


@pytest.mark.order(1)
class TestCreateProject:
    """Test project creation scenarios"""

    def test_create_project_hdf5(self, client: TestClient, valid_hdf5_project: dict):
        """Test creating project with only HDF5 files"""
        response = client.post("/api/projects/", json=valid_hdf5_project)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Valid HDF5 Project"
        assert "id" in data
        assert "files" in data
        assert len(data["files"]) == 2

    def test_create_project_fits(self, client: TestClient, valid_fits_project: dict):
        """Test creating project with only FITS files"""
        response = client.post("/api/projects/", json=valid_fits_project)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Valid FITS Project"
        assert "id" in data
        assert "files" in data
        assert len(data["files"]) == 2

    def test_create_project_invalid_file_extensions(
        self, client: TestClient, invalid_extension_project: dict
    ):
        """Test creating project with invalid file extensions"""
        response = client.post("/api/projects/", json=invalid_extension_project)
        assert response.status_code == 422

        error_data = response.json()
        assert "error_code" in error_data
        assert error_data["error_code"] == "INVALID_FILE_EXTENSION"

    def test_create_project_mixed_file_types(
        self, client: TestClient, mixed_file_types_project: dict
    ):
        """Test creating project with mixed file types"""
        response = client.post("/api/projects/", json=mixed_file_types_project)
        assert response.status_code == 422

        error_data = response.json()
        assert "error_code" in error_data
        assert error_data["error_code"] == "MIXED_FILE_TYPES"

    def test_duplicate_project(self, client: TestClient):
        """Test creating duplicate project"""
        response = client.get("/api/projects/")
        data = response.json()
        project_id = data[0]["id"]
        pj_data = {"name": "ayy", "description": "duplicate"}
        response = client.post(f"/api/projects/{project_id}/duplicate", json=pj_data)
        assert response.status_code == 200

        assert response.json()["name"] == "ayy"
        assert response.json()["description"] == "duplicate"
        assert response.json()["favourite"] is False
        assert response.json()["files"] == data[0]["files"]


@pytest.mark.order(2)
class TestReadProjects:
    def test_read_projects(self, client: TestClient):
        response = client.get("/api/projects/")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 3

    def test_read_project(self, client: TestClient):
        response = client.get("/api/projects/")
        data = response.json()
        project_id = data[0]["id"]
        response = client.get(f"/api/projects/{project_id}")
        assert response.status_code == 200
        assert response.json()["id"] == project_id
        assert response.json()["last_opened"] is not None


@pytest.mark.order(3)
class TestUpdateProject:
    """Test project update scenarios"""

    def test_update_project(self, client: TestClient):
        response = client.get("/api/projects/")
        data = response.json()
        project_id = data[0]["id"]
        update_data = {"name": "Updated Project", "description": "updated"}
        response = client.put(f"/api/projects/{project_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Project"
        assert data["description"] == "updated"

    def test_update_project_files(self, client: TestClient):
        """Test updating project with valid data"""
        response = client.get("/api/projects/")
        data = response.json()
        project_id = data[0]["id"]
        update_data = {
            "paths": ["file3.hdf5", "file4.hdf5"],
        }
        response = client.put(f"/api/projects/{project_id}/files", json=update_data)
        assert response.status_code == 200
        data = response.json()

        file_paths = [f["path"] for f in data["files"]]
        assert set(file_paths) == set(["file3.hdf5", "file4.hdf5"])

    def test_update_project_file_order(self, client: TestClient):
        """Test updating project file order"""
        response = client.get("/api/projects/")
        data = response.json()
        project_id = data[0]["id"]
        project = data[0]

        file_ids = [f["id"] for f in project["files"]]
        reversed_file_ids = list(reversed(file_ids))

        update_data = {
            "name": project["name"],
            "favourite": project["favourite"],
            "description": project["description"],
            "order": reversed_file_ids,
        }
        response = client.put(f"/api/projects/{project_id}", json=update_data)
        assert response.status_code == 200
        updated_data = response.json()

        updated_file_ids = [f["id"] for f in updated_data["files"]]
        assert updated_file_ids == reversed_file_ids


@pytest.mark.order(-1)
class TestDeleteProject:
    """Test project deletion scenarios"""

    def test_delete_project(self, client: TestClient):
        response = client.get("/api/projects/")
        data = response.json()
        project_id = data[0]["id"]
        response = client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 200
        data = response.json()

        assert data == {"message": "Project deleted successfully"}
