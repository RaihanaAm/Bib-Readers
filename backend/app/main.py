"""
Application FastAPI pour BibReaders.

Fonctionnalités :
- /health : vérifie que l'API tourne
- /db-ping : vérifie la connexion à la base (SELECT 1)
- /api/livres... (endpoints existants)
- /api/auth/...  (nouveaux endpoints)
- Sert les pages frontend : /, /detail, /reco
- Supporte CORS pour le développement
"""

import os
from pathlib import Path
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.routes import livres as livres_router
from app.routes import auth as auth_router


app = FastAPI(title="BibReaders API", version="0.1.0")

# CORS: open for dev (à restreindre en prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Endpoints basiques ===
@app.get("/health")
async def health() -> JSONResponse:
    """Retourne 'ok' si le serveur est vivant."""
    return JSONResponse({"status": "ok"})


@app.get("/db-ping")
async def db_ping(session: AsyncSession = Depends(get_session)) -> dict:
    """
    Exécute SELECT 1 pour confirmer l'accès DB.
    Retourne {"db":1} si OK.
    """
    result = await session.execute(text("SELECT 1"))
    return {"db": result.scalar_one()}


# === Routes API ===
app.include_router(livres_router.router)
app.include_router(auth_router.router)

# === Gestion du frontend ===
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "frontend" / "templates")

# Monter le dossier static
app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend" / "static"), name="static")

# Pages HTML avec Jinja2
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


# Pages HTML servies en statique pur (alternative)
FRONT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.isdir(FRONT_DIR):
    app.mount("/ui", StaticFiles(directory=FRONT_DIR), name="ui")

    @app.get("/detail")
    async def detail_ui():
        return FileResponse(os.path.join(FRONT_DIR, "detail.html"))

    @app.get("/reco")
    async def reco_ui():
        return FileResponse(os.path.join(FRONT_DIR, "reco.html"))
