import time
import threading
import requests
import docker

BASE_URL = "http://localhost:8000/api"

CREATE_PAYLOAD = {
    "name": "Test Project",
    "description": "A test project",
    # "paths": ["/app/data/snapshot_047.hdf5", "/app/data/ngc2403_fixed.fits"],
    "paths": ["/app/data/snapshot_047.hdf5"],
    # "paths": ["/app/data/ngc2403_fixed.fits"],
    # "config_process": {"downsampling": True, "variables": ["var1", "var2"]},
}


def create_project():
    response = requests.post(f"{BASE_URL}/projects/", json=CREATE_PAYLOAD)
    if response.status_code == 200:
        project_data = response.json()
        return project_data
    else:
        print(f"Failed to create project: {response.text}")
        return None


def process_project(project_id, process_payload):
    response = requests.post(
        f"{BASE_URL}/projects/{project_id}/process", json=process_payload
    )
    return response.status_code == 200


def get_container_memory_usage(container_name):
    client = docker.from_env()
    container = client.containers.get(container_name)
    stats = container.stats(stream=False)
    return stats["memory_stats"]["usage"] / (1024 * 1024)


def delete_project(project_id):
    response = requests.delete(f"{BASE_URL}/projects/{project_id}")
    return response.status_code == 200


def run_test():
    client = docker.from_env()
    container = client.containers.get("astroapi-api-1")

    memory_readings = []
    start_time = time.time()

    # Start memory tracking in a separate thread
    def track_memory():
        while tracking:
            try:
                stats = container.stats(stream=False)
                mem_usage = stats["memory_stats"]["usage"] / (1024 * 1024)
                memory_readings.append((time.time() - start_time, mem_usage))
                time.sleep(0.2)
            except Exception as e:
                print(f"Error tracking memory: {e}")
                break

    tracking = True
    memory_thread = threading.Thread(target=track_memory)
    memory_thread.daemon = True
    memory_thread.start()

    response = create_project()
    project_id = response["id"]
    if project_id is None:
        tracking = False
        return

    project_creation_time = time.time() - start_time

    # Process project code
    process_payload = response["config_process"]
    for var in process_payload["variables"]:
        process_payload["variables"][var]["thr_min_sel"] = (
            process_payload["variables"][var]["thr_min"]
            + 0.2 * process_payload["variables"][var]["thr_min"]
        )
        process_payload["variables"][var]["thr_max_sel"] = (
            process_payload["variables"][var]["thr_max"]
            - 0.2 * process_payload["variables"][var]["thr_max"]
        )
        if var not in ["pos", "vel"]:
            process_payload["variables"][var]["selected"] = True

    if process_project(project_id, process_payload):
        print("Project processed successfully.")
    else:
        print("Project processing failed.")

    project_processing_time = time.time() - start_time - project_creation_time

    # Stop memory tracking
    tracking = False
    memory_thread.join(timeout=1.0)

    # Report results
    max_memory = max(memory_readings, key=lambda x: x[1]) if memory_readings else (0, 0)
    print(f"Max Memory Usage: {max_memory[1]:.2f} MB (at {max_memory[0]:.2f}s)")
    print(
        f"Average Memory Usage: {sum([x[1] for x in memory_readings]) / len(memory_readings):.2f} MB"
    )
    print(f"Project Creation Time: {project_creation_time:.2f} seconds")
    print(f"Project Processing Time: {project_processing_time:.2f} seconds")

    delete_project(project_id)


if __name__ == "__main__":
    run_test()
