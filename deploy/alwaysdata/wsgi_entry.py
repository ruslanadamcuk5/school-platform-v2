"""WSGI entry point for Alwaysdata Python WSGI (uWSGI) sites.

The project's primary runtime is Uvicorn (ASGI). The pilot site on Alwaysdata
was created as a Python WSGI site, so this adapter exposes FastAPI through
a2wsgi. Copy this file to ``backend/__init__.py`` on the server only.

Install the adapter in the project virtualenv::

    pip install a2wsgi==1.10.10
"""
from __future__ import annotations

import sys
from pathlib import Path

HOME = Path.home()
for site_packages in (HOME / ".virtualenvs" / "school-platform" / "lib").glob(
    "python*/site-packages"
):
    sys.path.insert(0, str(site_packages))

from a2wsgi import ASGIMiddleware  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402

application = ASGIMiddleware(fastapi_app)
