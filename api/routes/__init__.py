"""
api/routes/__init__.py

Package marker for the api.routes sub-package.
Import the routers here so main.py can do:
    from api.routes import router
"""

from api.routes.intelligence import router  # noqa: F401 — re-exported for main.py
