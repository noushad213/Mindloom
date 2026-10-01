from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.db.session import get_db
from app.db.session import SessionLocal
from app.api.pages import router as pages_router
from app.api.processing import router as processing_router
from app.api.graph import router as graph_router
from app.api.annotations import router as annotations_router
from app.api.search import router as search_router
from app.api.sharing import router as sharing_router
from app.api.export import router as export_router
from app.api.workspaces import router as workspaces_router
from app.services.auth import edit_allowed, resource_workspace, valid_share
from app.jobs.queue import JobQueue
from app.ws.manager import ConnectionManager
from app.ws.router import router as ws_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    session_factory = getattr(application.state, "session_factory", SessionLocal)
    queue = JobQueue(session_factory, application.state.ws_manager, concurrency=2)
    application.state.job_queue = queue
    await queue.start()
    try:
        yield
    finally:
        await queue.stop()


app = FastAPI(title="Mindloom API", version="0.1.0", lifespan=lifespan)
app.state.ws_manager = ConnectionManager()
app.include_router(workspaces_router)
app.include_router(pages_router)
app.include_router(processing_router)
app.include_router(graph_router)
app.include_router(annotations_router)
app.include_router(search_router)
app.include_router(sharing_router)
app.include_router(export_router)
app.include_router(ws_router)


@app.middleware("http")
async def shared_access(request: Request, call_next):
    token = request.headers.get("X-Share-Token") or request.query_params.get("share")
    if not token or not request.url.path.startswith("/api/v1/") or request.url.path.startswith("/api/v1/shared/"):
        return await call_next(request)
    factory = getattr(request.app.state, "session_factory", SessionLocal)
    with factory() as db:
        link = valid_share(db, token)
        if link is None:
            return error_response(403, "forbidden", "Invalid or expired share token")
        target_workspace = resource_workspace(db, request.url.path)
        if target_workspace is not None and target_workspace != link.workspace_id:
            return error_response(404, "not_found", "Resource not found")
        if request.method != "GET" and (link.role == "view" or not edit_allowed(request.method, request.url.path)):
            return error_response(403, "forbidden", "Share token cannot perform this action")
        if request.url.path == "/api/v1/workspaces":
            request.state.shared_workspace_id = link.workspace_id
        request.state.share_role = link.role
    return await call_next(request)


@app.middleware("http")
async def limit_ingest_body(request: Request, call_next):
    if request.method == "POST" and request.url.path.startswith("/api/v1/workspaces/") and request.url.path.endswith("/pages"):
        limit = 2 * 1024 * 1024
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > limit:
                    return error_response(413, "payload_too_large", "Request body exceeds 2 MB")
            except ValueError:
                return error_response(422, "validation_error", "Invalid Content-Length header")
        if len(await request.body()) > limit:
            return error_response(413, "payload_too_large", "Request body exceeds 2 MB")
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Client", "X-Share-Token"],
)


def error_response(status_code: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


@app.exception_handler(StarletteHTTPException)
async def http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {403: "forbidden", 404: "not_found", 409: "conflict", 413: "payload_too_large", 422: "validation_error"}.get(
        exc.status_code, "validation_error" if exc.status_code < 500 else "internal_error"
    )
    if exc.status_code == 422 and exc.detail == "excluded_domain":
        code = "excluded_domain"
    return error_response(exc.status_code, code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0]
    field = ".".join(str(part) for part in first["loc"] if part != "body")
    return error_response(422, "validation_error", first["msg"], {"field": field})


@app.exception_handler(IntegrityError)
async def integrity_error(_request: Request, _exc: IntegrityError) -> JSONResponse:
    return error_response(409, "conflict", "Resource conflicts with an existing record")


@app.exception_handler(Exception)
async def internal_error(_request: Request, _exc: Exception) -> JSONResponse:
    return error_response(500, "internal_error", "Internal server error")


@app.get("/api/v1/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="Database unavailable") from exc
    return {"status": "ok", "version": "0.1.0", "db": "ok"}
