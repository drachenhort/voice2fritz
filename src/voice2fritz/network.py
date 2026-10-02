import fcntl
import socket
import struct
from dataclasses import dataclass
from pathlib import Path

_SIOCGIFADDR = 0x8915
_ARPHRD_LOOPBACK = 772
_ARPHRD_NONE = 65534  # WireGuard and tun devices (e.g. Tailscale)
_SYS_NET = Path("/sys/class/net")


@dataclass
class AddressInfo:
    address: str
    interface: str | None
    kind: str  # "Local network", "VPN", "Virtual network", "Loopback" or "Unknown"


def interface_for_address(address: str) -> str | None:
    """Name of the interface carrying this IPv4 address, or None."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        for _, name in socket.if_nameindex():
            try:
                request = struct.pack("256s", name[:15].encode())
                reply = fcntl.ioctl(probe.fileno(), _SIOCGIFADDR, request)
            except OSError:
                continue  # interface without an IPv4 address
            if socket.inet_ntoa(reply[20:24]) == address:
                return name
    return None


def classify_interface(name: str, sys_net: Path = _SYS_NET) -> str:
    path = sys_net / name
    try:
        arp_type = int((path / "type").read_text())
    except (OSError, ValueError):
        return "Unknown"
    if arp_type == _ARPHRD_LOOPBACK:
        return "Loopback"
    if (path / "device").exists():
        return "Local network"
    if arp_type == _ARPHRD_NONE or (path / "tun_flags").exists():
        return "VPN"
    return "Virtual network"


def describe_address(address: str) -> AddressInfo:
    interface = interface_for_address(address)
    kind = classify_interface(interface) if interface else "Unknown"
    return AddressInfo(address=address, interface=interface, kind=kind)
