# AstroAPI

AstroAPI is a Dockerized application that provides an API for astronomical data. This guide will help you set up and run the application.

## Prerequisites

- Docker (+ compose) installed on your system

## Installation and Usage

2. Build and start the Docker containers:

   ```bash
   docker compose up --build
   ```

3. Access the API at `http://localhost:8000`.

4. Open the documentation at the `/docs` endpoint:

   ```
   http://localhost:8000/docs
   ```

## Volumes

The application uses a volume to store data:

- Host directory: `${VOLUME_SOURCE}/astrodata`
- Container directory: `/app/data`

Ensure the `VOLUME_SOURCE` environment variable is set correctly before running the application.

