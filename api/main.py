from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from api.db import create_db_and_tables
from api.error_handlers import (
    api_exception_handler,
    pydantic_validation_exception_handler,
    sqlalchemy_exception_handler,
)
from api.exceptions import APIException
from api.routes.projects import router as projects_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(RequestValidationError, pydantic_validation_exception_handler)


@app.get("/api/health")
def health():
    return {"status": "OK"}


app.include_router(projects_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
