# backend/app/main.py
"""
FastAPI entrypoint for BibReaders.

- CORS (dev)
- /health, /db-ping
- /api/livres... (existing)
- /api/auth/...  (new)
- Serves frontend pages: /, /detail, /reco
"""
import os
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.routes import livres as livres_router
from app.routes import auth as auth_router


app = FastAPI(title="BibReaders API", version="0.1.0")

# CORS: open for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/db-ping")
async def db_ping(session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(text("SELECT 1"))
    return {"db": result.scalar_one()}


# Routers
app.include_router(livres_router.router)
app.include_router(auth_router.router)


# Frontend static mounting
FRONT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.isdir(FRONT_DIR):
    app.mount("/ui", StaticFiles(directory=FRONT_DIR), name="ui")

    @app.get("/")
    async def root_ui():
        return FileResponse(os.path.join(FRONT_DIR, "index.html"))

    @app.get("/detail")
    async def detail_ui():
        return FileResponse(os.path.join(FRONT_DIR, "detail.html"))

    @app.get("/reco")
    async def reco_ui():
        return FileResponse(os.path.join(FRONT_DIR, "reco.html"))
