import pytest
from fastapi.testclient import TestClient


@pytest.mark.order(4)
class TestFiles:
    """Test file-related scenarios"""

    def test_get_file(self, client: TestClient):
        """Test retrieving a file"""
        response = client.get("/api/projects/1")
        data = response.json()
        file_ids = [f["id"] for f in data["files"]]
        for f in file_ids:
            file_response = client.get(f"/api/projects/1/file/{f}")
            assert file_response.status_code == 200
            assert file_response.json()["id"] == f
            assert "variables" in file_response.json()
            assert len(file_response.json()["variables"]) > 0

    def test_update_file_variables(self, client: TestClient):
        """Test updating file variables"""
        response = client.get("/api/projects/1")
        data = response.json()
        file_ids = [f["id"] for f in data["files"]]
        for f in file_ids:
            file_response = client.get(f"/api/projects/1/file/{f}")
            file_data = file_response.json()
            variables = file_data["variables"]
            assert len(variables) > 0

            # Update the first variable
            var_to_update = variables[0]
            update_payload = {
                "thr_min_sel": var_to_update["thr_min"],
                "thr_max_sel": var_to_update["thr_max"],
                "selected": True,
                "x_axis": True,
            }
            file_data["variables"][0].update(update_payload)
            update_response = client.put(
                f"/api/projects/1/file/{f}/",
                json=file_data,
            )
            assert update_response.status_code == 200
            updated_file_data = update_response.json()
            assert (
                updated_file_data["variables"][0]["thr_min_sel"]
                == var_to_update["thr_min"]
            )
            assert (
                updated_file_data["variables"][0]["thr_max_sel"]
                == var_to_update["thr_max"]
            )
            assert updated_file_data["variables"][0]["selected"] is True
            assert updated_file_data["variables"][0]["x_axis"] is True
