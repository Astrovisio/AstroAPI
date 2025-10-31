# AstroAPI

**AstroAPI** is a Dockerized RESTful API designed to manage and process astrophysical data projects. While it functions as a standalone service, it is primarily intended to offload data processing tasks from Astrovisio's [Unity desktop application](https://github.com/Astrovisio/astrovisio-unity).
This guide will help you set up and run the application.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose installed on your system  
  >  [Windows Installation Guide](https://docs.docker.com/desktop/setup/install/windows-install/)

## Installation and Usage

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Astrovisio/AstroAPI.git
   cd AstroAPI
   ```
2. **Create a `.env` File**:
   
   This file should define the path to your local data directory. The data must be stored in a folder named astrodata.
   Example `.env`:
   ```
   VOLUME_SOURCE=/path/to/data
   ```
   > Docker mounts this folder as a volume, enabling the API to read your data and store its own objects within the same directory.
   It is mandatory that the data is kept in a "astrodata" named folder. 
   Docker will use that folder as a docker volume, and will be able to read your data, and store API-related objects in there.

3. **Build and Start the Application**:

   ```bash
   docker compose up --build
   ```

   - The API works on port 8000. Make sure it is free and available on your system.
   - The mandatory steps finish here. Now you can start using the Unity application! For more low-level users, the API can be accessed at `http://localhost:8000`.
   The documentation is accessible at `http://localhost:8000/docs`.

## Data model concepts (high level)

- Project: A collection of files plus per-variable configurations.
- File: FITS or HDF5, discovered via provided paths.
- Variable: Metadata and thresholds per file.
- Histograms: Persisted per variable to support UI exploration.
- Render settings: Per selected variable (noise, thresholds, etc.).
- Processing: Background job creates a processed artifact (cached).

## API quick reference

Projects:
- GET /projects — List projects
- POST /projects — Create project (with file paths)
- GET /projects/{project_id} — Get project
- PUT /projects/{project_id} — Update project metadata and file order
- DELETE /projects/{project_id} — Delete project
- POST /projects/{project_id}/duplicate — Duplicate project
- PUT /projects/{project_id}/files — Replace all files in a project

Files:
- GET /projects/{project_id}/file/{file_id} — Get file + variable configurations
- PUT /projects/{project_id}/file/{file_id} — Update file + variable configs
- POST /projects/{project_id}/file/{file_id}/process — Start processing (returns job_id)
- GET /projects/{project_id}/file/{file_id}/process — Download processed file (404 if missing, 400 if not ready)
- GET /projects/{project_id}/file/{file_id}/render — Get render settings
- PUT /projects/{project_id}/file/{file_id}/render — Update render settings
- GET /projects/{project_id}/file/{file_id}/histos — Get histograms for all variables

See the schemas and try requests in /docs.
