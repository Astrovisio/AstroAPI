from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager

from api.db import create_db_and_tables
from api.routes.projects import router as projects_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/api/health")
def health():
    return {"status": "OK"}


app.include_router(projects_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
