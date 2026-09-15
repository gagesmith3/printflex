"""Work out the address phones should use to reach this server."""

import socket


def lan_ip() -> str:
    """Best guess at this machine's LAN IP, or 127.0.0.1 when there is no network."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # A UDP connect sends nothing; it only asks the OS which interface would be used.
        probe.connect(("10.254.254.254", 1))
        ip = probe.getsockname()[0]
    except OSError:
        ip = None
    finally:
        probe.close()
    if ip and not ip.startswith("127."):
        return ip
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            if not info[4][0].startswith("127."):
                return info[4][0]
    except OSError:
        pass
    return "127.0.0.1"


def base_url(public_host: str, port: int) -> str:
    host = public_host or lan_ip()
    return f"http://{host}" if port == 80 else f"http://{host}:{port}"
