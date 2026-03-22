"""
core_backend/limiter.py

Shared SlowAPI rate limiter instance.

Defined here instead of main.py to avoid circular imports:
  main.py imports routes → routes would import from main → circular.
  Instead, both main.py and routes import from this module.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Uses the client IP address as the rate limiting key.
limiter = Limiter(key_func=get_remote_address)
