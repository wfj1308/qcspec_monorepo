"""Database infrastructure exports."""

from services.api.supabase_provider import get_supabase_client

__all__ = ["get_supabase_client"]
