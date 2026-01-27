# =============================================================================
# SERV.O v8.2 - FASTAPI MAIN
# =============================================================================
# Applicazione FastAPI principale
# =============================================================================

from .routers import (
    upload,
    ordini,
    anagrafica,
    tracciati,
    anomalie,
    dashboard,
    lookup,
    supervisione,
    admin,
    mail,
    produttivita,
    listini,
    backup,
    email,  # v8.1 - Configurazione email
    crm,    # v8.1 - Sistema CRM/Ticketing
    report,  # v8.1 - Report esportazione Excel
)
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from .config import config
from .database_pg import init_database, get_stats
from .services.scheduler import (
    init_mail_scheduler,
    init_anagrafica_scheduler,
    shutdown_all_schedulers
)

# Import router autenticazione (NUOVO v6.2)
from .auth import auth_router
from .routers.utenti import router as utenti_router


# =============================================================================
# LIFESPAN - Startup/Shutdown
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestisce startup e shutdown dell'applicazione."""
    # Startup
    print("🚀 SERV.O v11.3 - Avvio...")

    # Crea directories
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    # Inizializza database
    init_database()

    stats = get_stats()
    print(f"✅ Database inizializzato")
    print(f"   📊 Farmacie: {stats['farmacie']:,}")
    print(f"   📊 Parafarmacie: {stats['parafarmacie']:,}")
    print(f"   📊 Ordini: {stats['ordini']:,}")

    # Inizializza Schedulers
    init_mail_scheduler()
    init_anagrafica_scheduler()  # v11.2: Sync anagrafica Lun-Ven 06:30

    yield

    # Shutdown
    shutdown_all_schedulers()
    print("👋 SERV.O - Arresto...")


# =============================================================================
# APP FASTAPI
# =============================================================================

app = FastAPI(
    title="SERV.O API",
    description="Sistema estrazione Transfer Order per farmacie",
    version="8.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# CORS MIDDLEWARE
# =============================================================================

# Origini consentite per CORS
ALLOWED_ORIGINS = [
    "http://localhost:3000",      # React dev
    "http://localhost:5173",      # Vite dev
    "http://localhost:8080",      # Vue dev
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
    "https://*.github.dev",       # GitHub Codespaces
    "https://*.preview.app.github.dev",
    "https://sofad.aiservo.net",           # Production frontend
    "https://api-sofad.aiservo.net",      # Production backend
    "https://servo-frontend.onrender.com", # Render frontend
    "https://servo-backend.onrender.com",  # Render backend
]

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# =============================================================================
# STATIC FILES
# =============================================================================

# Monta directory per file statici (output tracciati)
if os.path.exists(config.OUTPUT_DIR):
    app.mount("/files", StaticFiles(directory=config.OUTPUT_DIR), name="files")


# =============================================================================
# ROUTERS
# =============================================================================

# Prefisso API
API_PREFIX = "/api/v1"

# Router esistenti
app.include_router(dashboard.router, prefix=API_PREFIX, tags=["Dashboard"])
app.include_router(upload.router, prefix=API_PREFIX, tags=["Upload"])
app.include_router(ordini.router, prefix=API_PREFIX, tags=["Ordini"])
app.include_router(anagrafica.router, prefix=API_PREFIX, tags=["Anagrafica"])
app.include_router(tracciati.router, prefix=API_PREFIX, tags=["Tracciati"])
app.include_router(anomalie.router, prefix=API_PREFIX, tags=["Anomalie"])
app.include_router(lookup.router, prefix=API_PREFIX, tags=["Lookup"])
app.include_router(supervisione.router, prefix=API_PREFIX,
                   tags=["Supervisione"])

# Router autenticazione (NUOVO v6.2)
app.include_router(auth_router, prefix=API_PREFIX, tags=["Autenticazione"])
app.include_router(utenti_router, prefix=API_PREFIX, tags=["Gestione Utenti"])

# Router admin (backup, reset, settings)
app.include_router(admin.router, prefix=API_PREFIX, tags=["Admin"])

# Router Mail Monitor (v6.2)
app.include_router(mail.router, prefix=API_PREFIX, tags=["Mail Monitor"])

# Router Produttività (v6.2)
app.include_router(produttivita.router, prefix=API_PREFIX, tags=["Produttività"])

# Router Listini Vendor (v7.0)
app.include_router(listini.router, prefix=API_PREFIX, tags=["Listini Vendor"])

# Router Backup System (v9.0)
app.include_router(backup.router, prefix=API_PREFIX, tags=["Backup"])

# Router Email Config (v8.1)
app.include_router(email.router, prefix=API_PREFIX, tags=["Email Config"])

# Router CRM/Ticketing (v8.1)
app.include_router(crm.router, prefix=API_PREFIX, tags=["CRM"])

# Router Report Export (v8.1)
app.include_router(report.router, prefix=API_PREFIX, tags=["Report"])

# Router Permessi (v10.0)
from .routers import permessi
app.include_router(permessi.router, prefix=API_PREFIX, tags=["Permessi"])


# =============================================================================
# ROOT ENDPOINTS
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Endpoint root - info applicazione."""
    return {
        "app": "SERV.O",
        "version": "8.2.0",
        "status": "running",
        "docs": "/docs",
        "api": "/api/v1"
    }


@app.get("/health", tags=["Root"])
async def health_check():
    """Health check endpoint."""
    try:
        stats = get_stats()
        return {
            "status": "healthy",
            "database": "connected",
            "stats": stats
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@app.get("/api/v1", tags=["Root"])
async def api_info():
    """Info API v1."""
    return {
        "version": "1.0",
        "endpoints": {
            "dashboard": "/api/v1/dashboard",
            "upload": "/api/v1/upload",
            "ordini": "/api/v1/ordini",
            "anagrafica": "/api/v1/anagrafica",
            "tracciati": "/api/v1/tracciati",
            "anomalie": "/api/v1/anomalie",
            "lookup": "/api/v1/lookup",
            "supervisione": "/api/v1/supervisione",
            "auth": "/api/v1/auth",
            "utenti": "/api/v1/utenti",
            "admin": "/api/v1/admin",
            "mail": "/api/v1/mail",
            "backup": "/api/v1/backup",
        }
    }


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handler globale per eccezioni non gestite."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "path": str(request.url)
        }
    )


# =============================================================================
# RUN (per sviluppo)
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
