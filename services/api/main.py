"""QCSpec FastAPI backend entrypoint."""

from services.api.infrastructure.http import create_app

app = create_app()
