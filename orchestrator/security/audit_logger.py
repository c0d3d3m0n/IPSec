import hashlib
import json
import importlib.util
import sys
from pathlib import Path
from typing import Any


def _load_audit_model():
    module_name = "orchestrator_models_audit"
    if module_name in sys.modules:
        return sys.modules[module_name]

    file_path = Path(__file__).resolve().parents[1] / "models" / "audit.py"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load audit model module")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class AuditLogger:
    def log(self, action: str, actor: str, target: str, payload_dict: dict[str, Any], ip_address: str | None, db):
        audit_module = _load_audit_model()
        AuditLog = audit_module.AuditLog

        payload_json = json.dumps(payload_dict, sort_keys=True, default=str)
        payload_hash = hashlib.sha512(payload_json.encode("utf-8")).hexdigest()

        previous = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        previous_chain_hash = previous.chain_hash if previous else ""
        chain_hash = hashlib.sha512(f"{previous_chain_hash}{payload_hash}".encode("utf-8")).hexdigest()

        record = AuditLog(
            action=action,
            actor=actor,
            target=target,
            payload_hash=payload_hash,
            ip_address=ip_address,
            chain_hash=chain_hash,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
