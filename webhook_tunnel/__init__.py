"""
Webhook Tunnel - Expose local ports with custom DNS for webhook testing
"""

__version__ = "1.0.0"
__author__ = "Joao Pedro Albergaria de Castro"
__license__ = "MIT"

from .manager import TunnelManager

__all__ = ["TunnelManager", "__version__"]
