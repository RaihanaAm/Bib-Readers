"""
Application FastAPI minimale avec deux endpoints:
- /health : vérifie que l'API tourne
- /db-ping : vérifie la connexion à la base (SELECT 1)
"""
from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session

app = FastAPI(title="BibReaders API", version="0.1.0")

@app.get("/health")
async def health():
    """Retourne 'ok' si le serveur est vivant."""
    return JSONResponse({"status": "ok"})

@app.get("/db-ping")
async def db_ping(session: AsyncSession = Depends(get_session)):
    """
    Exécute SELECT 1 pour confirmer l'accès DB.
    Retourne {"db":1} si OK.
    """
    result = await session.execute(text("SELECT 1"))
    return {"db": result.scalar_one()}
