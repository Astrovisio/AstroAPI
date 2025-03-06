from fastapi.testclient import TestClient


def test_create_new_project(client: TestClient, new_project: dict):
    response = client.post("/api/projects/", json=new_project)
    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Test Project"
    assert data["description"] == "A test project"
    assert data["paths"] == ["file1", "file2"]
    assert "config_process" in data.keys()
    assert "downsampling" in data["config_process"].keys()
    assert "variables" in data["config_process"].keys()


def test_read_projects(client: TestClient):
    response = client.get("/api/projects/")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 1


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
    update_data = {"name": "Updated Project", "paths": ["file3", "file4"]}
    response = client.put(f"/api/projects/{project_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Updated Project"
    assert set(data["paths"]) == set(["file3", "file4"])


def test_delete_project(client: TestClient):
    response = client.get("/api/projects/")
    data = response.json()
    project_id = data[0]["id"]
    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()

    assert data == {"message": "Project deleted successfully"}
