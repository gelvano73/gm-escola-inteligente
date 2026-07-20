from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.migrate import ensure_schema_upgrades
from app.routers import academico, acesso, alunos, auth, dashboard, escola, eventos, lgpd, noticias, notas, ocorrencias, professores, relatorios, whatsapp
from app.seed import seed_database

settings = get_settings()
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_CANDIDATE_FRONTENDS = [
    _BACKEND_ROOT.parent / "frontend",
    _BACKEND_ROOT / "frontend",
]
FRONTEND_DIR = next((p for p in _CANDIDATE_FRONTENDS if p.exists()), _CANDIDATE_FRONTENDS[0])


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_schema_upgrades()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API REST do sistema escolar G&M Escola Inteligente (1º Ano Fundamental ao 3º Ano Médio).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(alunos.router, prefix="/api")
app.include_router(professores.router, prefix="/api")
app.include_router(academico.router, prefix="/api")
app.include_router(notas.router, prefix="/api")
app.include_router(ocorrencias.router, prefix="/api")
app.include_router(eventos.router, prefix="/api")
app.include_router(noticias.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(acesso.router, prefix="/api")
app.include_router(relatorios.router, prefix="/api")
app.include_router(escola.router, prefix="/api")
app.include_router(whatsapp.router, prefix="/api")
app.include_router(lgpd.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


UPLOADS_DIR = _BACKEND_ROOT / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/boletim")
    def boletim_login():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/admin")
    def admin_login():
        return FileResponse(FRONTEND_DIR / "pages" / "admin-login.html")

    @app.get("/equipe")
    def equipe_login():
        return FileResponse(FRONTEND_DIR / "pages" / "admin-login.html")

    @app.get("/pages/{page_name}")
    def serve_page(page_name: str):
        target = FRONTEND_DIR / "pages" / page_name
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail="Página não encontrada")
        return FileResponse(target)
