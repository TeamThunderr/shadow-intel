"""
Ownership Unwind Agent Module redirect.
Exposes the real implementation defined in service.py.
"""

from .service import OwnershipUnwindAgent

__all__ = ["OwnershipUnwindAgent"]
