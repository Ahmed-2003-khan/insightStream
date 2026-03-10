"""
main.py

Application entry point for InsightStream.

This file is intentionally thin. Its only responsibilities are:
  1. Create the FastAPI application instance.
  2. Register all routers (route modules) onto that instance.
  3. (Optionally) configure global middleware, CORS, or startup/shutdown events.

All actual routing logic lives in api/routes.py, keeping this file clean
and easy to extend as the project grows.
"""

from fastapi import FastAPI

# Import the router defined in api/routes.py. The router carries all of the
# endpoint definitions for the intelligence layer. By importing and including
# it here, we attach those routes to the top-level FastAPI application.
from api.routes import router

# ── Application Initialization ────────────────────────────────────────────────
# FastAPI() creates the ASGI application object. The title and version appear
# in the auto-generated OpenAPI docs (accessible at /docs once the server is
# running), which makes the API self-documenting out of the box.
app = FastAPI(
    title="InsightStream Intelligence API",
    version="1.0.0",
    description=(
        "A Retrieval-Augmented Generation (RAG) API that answers competitive "
        "intelligence queries by grounding LLM responses in curated knowledge."
    ),
)

# ── Router Registration ───────────────────────────────────────────────────────
# include_router() mounts all routes defined in api/routes.py onto the app.
# Because the full path (/api/v1/intelligence/query) is already declared on
# each endpoint inside routes.py, we do not need to add a prefix here.
# If we had multiple route modules (e.g., for users, reports, settings),
# we would call include_router() once for each, keeping concerns separated.
app.include_router(router)
