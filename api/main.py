from fastapi import FastAPI
import uvicorn

from api.db import create_db_and_tables
from api.routes.projects import router as projects_router


app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/api/health")
def health():
    return {"status": "OK"}


app.include_router(projects_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
