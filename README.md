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

