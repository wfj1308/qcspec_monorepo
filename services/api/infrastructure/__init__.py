"""Infrastructure layer exports."""

from services.api.infrastructure.database import get_supabase_client

__all__ = [
    "get_supabase_client",
]
