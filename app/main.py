from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.categories.router import router as categories_router
from app.core.config import settings
from app.engagement.router import router as engagement_router
from app.podcasts.router import router as podcasts_router
from app.posts.router import router as posts_router
from app.users.router import router as users_router
from app.writers.router import router as writers_router

app = FastAPI(title=settings.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Lets browser clients read the post count used for pagination.
    expose_headers=["X-Total-Count"],
)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    """Any error a route didn't handle (e.g. the database is down) becomes a JSON
    500. HTTPExceptions like 404 and 409 never reach here, and the traceback is
    still logged by the server."""
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(posts_router)
app.include_router(engagement_router)
app.include_router(writers_router)
app.include_router(podcasts_router)


@app.get("/")
def root():
    return {"message": "News 24. API V1 running"}


@app.get("/health")
def health():
    return {"status": "ok"}
