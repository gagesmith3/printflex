from .base import Hardware
from .mock import MockHardware


def get_hardware(config) -> Hardware:
    """v1 always uses the mock. The UNO Q implementation plugs in here later."""
    return MockHardware()
