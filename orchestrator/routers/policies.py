from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session
from typing import List, Any
import json
import importlib.util
import sys
from pathlib import Path
from .. import models, schemas, database

router = APIRouter(
    prefix="/policies",
    tags=["policies"]
)

from ..auth import get_current_admin_user


def _load_module(module_name: str, file_path: Path):
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_BASE_DIR = Path(__file__).resolve().parents[1]
_policy_parser_module = _load_module("orchestrator_services_policy_parser", _BASE_DIR / "services" / "policy_parser.py")
_audit_logger_module = _load_module("orchestrator_security_audit_logger", _BASE_DIR / "security" / "audit_logger.py")

PolicyParser = _policy_parser_module.PolicyParser
AuditLogger = _audit_logger_module.AuditLogger


def _safe_config_data(raw_value: Any) -> dict:
    if isinstance(raw_value, dict):
        return raw_value
    if raw_value is None:
        return {}
    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}

@router.post("/", response_model=schemas.PolicyResponse)
def create_policy(
    policy: schemas.UnifiedPolicyCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    db_policy = db.query(models.Policy).filter(models.Policy.name == policy.policy_id).first()
    if db_policy:
        raise HTTPException(status_code=400, detail="Policy with this name already exists")
    
    new_policy = models.Policy(
        name=policy.policy_id,
        description=policy.description,
        config_data=policy.model_dump_json()
    )
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)
    return new_policy

@router.post("/upload")
def upload_policies(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    allowed_types = {"application/json", "text/plain", "application/octet-stream"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    raw_bytes = file.file.read()
    if len(raw_bytes) > 512 * 1024:
        raise HTTPException(status_code=413, detail="Policy upload exceeds 512 KB")

    parser = PolicyParser()
    result = parser.parse(raw_bytes)

    try:
        original_payload = json.loads(raw_bytes.decode("utf-8")) if raw_bytes else {}
    except Exception:
        original_payload = {}

    if not result.is_valid:
        AuditLogger().log(
            action="POLICY_UPLOAD_FAILED",
            actor=current_user.username,
            target=str(original_payload.get("policy_id") or file.filename or "unknown"),
            payload_dict={"errors": result.errors, "warnings": result.warnings},
            ip_address=request.client.host if request.client else None,
            db=db,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Policy validation failed \u2014 nothing was stored",
                "errors": result.errors,
                "warnings": result.warnings,
            },
        )

    per_os_configs: dict[str, Any] = {}
    for os_name, os_config in result.os_configs.items():
        per_os_configs[os_name] = {
            "policy_id": result.policy_id,
            "version": result.version,
            "description": result.description,
            "ike_encryption": os_config.ike_encryption,
            "ike_integrity": os_config.ike_integrity,
            "ike_dh_group": os_config.ike_dh_group,
            "esp_encryption": os_config.esp_encryption,
            "esp_integrity": os_config.esp_integrity,
            "esp_dh_group": os_config.esp_dh_group,
            "key_exchange": os_config.key_exchange,
            "mode": os_config.mode,
            "connections": os_config.connections,
            "auth_type": os_config.auth_type,
            "auth_secret_ref": os_config.auth_secret_ref,
            "driver_block": os_config.raw_driver_block,
        }

    config_data = dict(original_payload)
    config_data["per_os_configs"] = per_os_configs
    config_data["input_hash"] = result.input_hash
    config_data["parse_warnings"] = result.warnings

    db_policy = db.query(models.Policy).filter(models.Policy.name == result.policy_id).first()
    if db_policy:
        db_policy.description = result.description
        db_policy.config_data = json.dumps(config_data)
    else:
        db_policy = models.Policy(
            name=result.policy_id,
            description=result.description,
            config_data=json.dumps(config_data),
        )
        db.add(db_policy)

    try:
        db.commit()
        db.refresh(db_policy)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process policy upload: {exc}")

    AuditLogger().log(
        action="POLICY_UPLOAD_SUCCESS",
        actor=current_user.username,
        target=str(db_policy.id),
        payload_dict={"policy_id": result.policy_id, "version": result.version, "warnings": result.warnings},
        ip_address=request.client.host if request.client else None,
        db=db,
    )

    os_summary: dict[str, Any] = {}
    for os_name, os_config in per_os_configs.items():
        os_summary[os_name] = {
            "ike": "/".join(part for part in [os_config["ike_encryption"], os_config["ike_integrity"], os_config["ike_dh_group"]] if part),
            "esp": "/".join(part for part in [os_config["esp_encryption"], os_config["esp_integrity"], os_config["esp_dh_group"]] if part),
            "mode": os_config["mode"],
            "connections": len(os_config["connections"]),
        }

    return {
        "status": "success",
        "policy_id": db_policy.id,
        "name": result.policy_id,
        "version": result.version,
        "target_os": list(per_os_configs.keys()),
        "warnings": result.warnings,
        "os_summary": os_summary,
        "message": f"Policy stored successfully for {len(per_os_configs)} OS target(s).",
    }

@router.get("/", response_model=List[schemas.PolicyResponse])
def read_policies(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    policies = db.query(models.Policy).offset(skip).limit(limit).all()
    for p in policies:
        p.config_data = _safe_config_data(p.config_data)
    return [schemas.PolicyResponse.model_validate(policy).model_dump(mode="json") for policy in policies]

@router.get("/{policy_id}", response_model=schemas.PolicyResponse)
def read_policy(
    policy_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy.config_data = _safe_config_data(policy.config_data)
    return schemas.PolicyResponse.model_validate(policy).model_dump(mode="json")

@router.post("/{policy_id}/assign/{device_id}")
def assign_policy(
    policy_id: int, 
    device_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    device.policy_id = policy.id
    db.commit()
    return {"message": "Policy assigned successfully"}

@router.delete("/unassign/{device_id}")
def unassign_policy(
    device_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    device.policy_id = None
    db.commit()
    return {"message": "Policy unassigned successfully"}

@router.delete("/{policy_id}")
def delete_policy(
    policy_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    # Unset policy_id for all devices using this policy
    db.query(models.Device).filter(models.Device.policy_id == policy_id).update({"policy_id": None})
    
    db.delete(policy)
    db.commit()
    return {"message": "Policy deleted successfully"}
