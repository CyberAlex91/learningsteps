from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
import asyncpg
from dotenv import load_dotenv
from routers.journal_router import router as journal_router
from routers.summary_router import router as summary_router
from security.dependencies import auth_settings, current_user
from security.identity import Principal
import logging
import sys
from contextlib import asynccontextmanager

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("journal")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LearningSteps API started")
    yield
    logger.info("LearningSteps API stopped")

app = FastAPI(
    title="LearningSteps API",
    description="Dein Lerntagebuch mit sicherer, nutzerbezogener KI-Zusammenfassung. Fuer die Anmeldung http://localhost:8000/docs verwenden.",
    lifespan=lifespan,
    swagger_ui_init_oauth={
        "clientId": auth_settings.swagger_client_id,
        "usePkceWithAuthorizationCodeGrant": True,
        "scopes": auth_settings.scope,
    },
)
app.include_router(journal_router)
app.include_router(summary_router)


@app.exception_handler(asyncpg.PostgresError)
async def database_error(request, exc):
    # No raw database exception: it may contain SQL parameters or note contents.
    logger.error("Database operation failed")
    return JSONResponse(status_code=503, content={"detail": "Die Datenbank ist momentan nicht bereit."})


@app.get("/me", tags=["Anmeldung"])
def me(user: Principal = Depends(current_user)):
    """Die vom Backend gepruefte Identitaet; niemals Zugriffstokens zurueckgeben."""
    return {"tenant_id": user.tenant_id, "object_id": user.object_id}


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")
