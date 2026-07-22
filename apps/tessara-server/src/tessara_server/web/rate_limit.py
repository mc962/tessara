"""Shared slowapi Limiter — routes import this directly (not from main.py) to avoid a
circular import, since main.py is what wires up all the route modules in the first place."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
