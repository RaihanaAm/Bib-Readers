#pour lancer le projet: py -m uvicorn main:app --reload


from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

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
