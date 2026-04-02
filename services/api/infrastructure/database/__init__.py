"""Database infrastructure exports."""

from services.api.infrastructure.database.provider import get_supabase_client

__all__ = ["get_supabase_client"]
