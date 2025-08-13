"""
Application FastAPI minimale avec deux endpoints:
- /health : vérifie que l'API tourne
- /db-ping : vérifie la connexion à la base (SELECT 1)
"""
#fast API
from fastapi import FastAPI, Depends,Request, Form
from fastapi.responses import JSONResponse ,HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session

app = FastAPI(title="BibReaders API", version="0.1.0")


# Dossier static pour CSS, images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dossier des templates
templates = Jinja2Templates(directory="templates")



#^^Page d'accueil
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


#^^ Page de connexion 
@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

#^^ Page de création de compte
@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})



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


