from voice2fritz.network import classify_interface, describe_address, interface_for_address


def _fake_interface(sys_net, name, arp_type, device=False, tun=False):
    path = sys_net / name
    path.mkdir()
    (path / "type").write_text(f"{arp_type}\n")
    if device:
        (path / "device").mkdir()
    if tun:
        (path / "tun_flags").write_text("0x1001\n")


def test_physical_interface_is_local_network(tmp_path):
    _fake_interface(tmp_path, "enp34s0", 1, device=True)
    assert classify_interface("enp34s0", tmp_path) == "Local network"


def test_wireguard_interface_is_vpn(tmp_path):
    _fake_interface(tmp_path, "Reykjavic-IS", 65534)
    assert classify_interface("Reykjavic-IS", tmp_path) == "VPN"


def test_tun_interface_is_vpn(tmp_path):
    _fake_interface(tmp_path, "tailscale0", 65534, tun=True)
    assert classify_interface("tailscale0", tmp_path) == "VPN"


def test_bridge_without_device_is_virtual_network(tmp_path):
    _fake_interface(tmp_path, "docker0", 1)
    assert classify_interface("docker0", tmp_path) == "Virtual network"


def test_loopback(tmp_path):
    _fake_interface(tmp_path, "lo", 772)
    assert classify_interface("lo", tmp_path) == "Loopback"


def test_missing_interface_is_unknown(tmp_path):
    assert classify_interface("gone0", tmp_path) == "Unknown"


def test_loopback_address_maps_to_lo():
    assert interface_for_address("127.0.0.1") == "lo"
    assert describe_address("127.0.0.1").kind == "Loopback"


def test_unassigned_address_is_unknown():
    info = describe_address("203.0.113.77")
    assert info.interface is None
    assert info.kind == "Unknown"


def test_interface_lookup_is_skipped_off_linux(monkeypatch):
    import sys

    monkeypatch.setattr(sys, "platform", "win32")
    assert interface_for_address("127.0.0.1") is None
    assert describe_address("127.0.0.1").kind == "Unknown"
