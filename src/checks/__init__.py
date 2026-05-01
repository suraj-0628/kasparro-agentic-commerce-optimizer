"""
src/checks/__init__.py
"""
from .faq_policy         import check_faq_and_policies
from .trust_signals      import check_store_trust
from .competitor_baseline import generate_competitive_context
from .query_simulator    import simulate_queries

__all__ = [
    "check_faq_and_policies",
    "check_store_trust",
    "generate_competitive_context",
    "simulate_queries",
]