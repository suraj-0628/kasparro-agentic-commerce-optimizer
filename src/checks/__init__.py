"""
src/checks/__init__.py
NEW FILE — makes checks/ a proper Python package.
"""
from .faq_policy    import check_faq_and_policies
from .trust_signals import check_store_trust

__all__ = ["check_faq_and_policies", "check_store_trust"]