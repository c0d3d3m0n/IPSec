import threading
import importlib
import logging
from ipaddress import ip_address, ip_network
from typing import Any


logger = logging.getLogger(__name__)


class LeakDetector:
    def __init__(self, protected_subnets: list[str]):
        self.protected_subnets = [ip_network(s, strict=False) for s in protected_subnets]
        self._lock = threading.Lock()
        self._leak_counter = 0
        self._thread: threading.Thread | None = None
        self._running = False

    def _is_protected_pair(self, src: str, dst: str) -> bool:
        try:
            src_ip = ip_address(src)
            dst_ip = ip_address(dst)
        except ValueError:
            return False

        src_protected = any(src_ip in net for net in self.protected_subnets)
        dst_protected = any(dst_ip in net for net in self.protected_subnets)
        return src_protected and dst_protected

    def packet_inspector(self, pkt: Any):
        if not pkt.haslayer("IP"):
            return

        src = pkt["IP"].src
        dst = pkt["IP"].dst
        proto = int(pkt["IP"].proto)

        # ESP is IP protocol 50; any protected-subnet traffic using another protocol is flagged.
        if self._is_protected_pair(src, dst) and proto != 50:
            with self._lock:
                self._leak_counter += 1

    def start(self, interface: str):
        try:
            scapy_all = importlib.import_module("scapy.all")
            sniff = getattr(scapy_all, "sniff")
            resolve_iface = getattr(scapy_all, "resolve_iface", None)
            conf = getattr(scapy_all, "conf", None)
        except Exception:
            # Scapy is optional; leak detection will remain passive if unavailable.
            return

        if self._running:
            return

        selected_interface = interface
        if resolve_iface is not None:
            try:
                resolve_iface(selected_interface)
            except Exception:
                fallback = str(getattr(conf, "iface", "") or "")
                if fallback:
                    logger.warning(
                        "Leak detector interface '%s' not found. Falling back to '%s'.",
                        selected_interface,
                        fallback,
                    )
                    selected_interface = fallback
                else:
                    logger.warning(
                        "Leak detector interface '%s' not found and no fallback is available. Disabling leak sniffing.",
                        selected_interface,
                    )
                    return

        self._running = True

        def _run():
            try:
                sniff(iface=selected_interface, prn=self.packet_inspector, store=False, stop_filter=lambda _: not self._running)
            except Exception as exc:
                logger.warning("Leak detector stopped due to sniff error: %s", exc)
                self._running = False

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def get_leak_status(self) -> bool:
        with self._lock:
            return self._leak_counter > 0

    def reset(self):
        with self._lock:
            self._leak_counter = 0
