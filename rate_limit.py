"""Shared slowapi rate limiter.

A single Limiter instance must be used both for the `@limiter.limit(...)`
route decorators and for `app.state.limiter` / the RateLimitExceeded handler.
Creating separate instances (as was done before) is fragile, so everything
imports this one.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
