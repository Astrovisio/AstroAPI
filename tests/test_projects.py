from fastapi.testclient import TestClient


def test_create_new_project(client: TestClient, new_project: dict):
    response = client.post("/api/projects/", json=new_project)
    assert response.status_code == 200
    data = response.json()
    print(data)
    assert data["name"] == new_project["name"]
    assert data["description"] == new_project["description"]


# def test_read_projects(client: TestClient):
#     response = client.get("/projects/")
#     assert response.status_code == 200
#     data = response.json()
#     assert isinstance(data, list)
