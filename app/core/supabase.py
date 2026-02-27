"""
Supabase client singletons.

- `supabase_client`       → uses the ANON key  (respects RLS — safe for user-scoped requests)
- `supabase_admin`        → uses the SERVICE ROLE key (bypasses RLS — server-side ops only)
"""
from functools import lru_cache

from supabase import create_client, Client

from app.core.config import settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Public/anon client — honours Row Level Security."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


@lru_cache(maxsize=1)
def get_supabase_admin() -> Client:
    """Service-role client — bypasses RLS. Use only for server-side logic."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


# Convenience module-level singletons
supabase_client: Client = get_supabase_client()
supabase_admin: Client = get_supabase_admin()
