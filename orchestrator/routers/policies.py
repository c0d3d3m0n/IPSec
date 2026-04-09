from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import json
from .. import models, schemas, database

router = APIRouter(
    prefix="/policies",
    tags=["policies"]
)

from ..auth import get_current_admin_user

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

@router.post("/upload", response_model=dict)
def upload_policies(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    try:
        content = file.file.read()
        data = json.loads(content)
        # Assuming either it's an array or wrapped in a 'policies' key
        if "policies" in data:
            bulk_upload = schemas.PolicyBulkUpload(**data)
        else:
            bulk_upload = schemas.PolicyBulkUpload(policies=[data])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format or schema: {e}")
    
    created_count = 0

    try:
        for policy_item in bulk_upload.policies:
            db_policy = db.query(models.Policy).filter(models.Policy.name == policy_item.policy_id).first()
            if db_policy:
                continue

            db_policy = models.Policy(
                name=policy_item.policy_id,
                description=policy_item.description,
                config_data=policy_item.model_dump_json()
            )
            db.add(db_policy)
            created_count += 1

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process policy upload: {e}")

    return {"message": f"Successfully processed JSON upload. Created {created_count} policies."}

@router.get("/", response_model=List[schemas.PolicyResponse])
def read_policies(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    policies = db.query(models.Policy).offset(skip).limit(limit).all()
    for p in policies:
        p.config_data = json.loads(p.config_data)  # Parse string back to dict for the API response
    return policies

@router.get("/{policy_id}", response_model=schemas.PolicyResponse)
def read_policy(
    policy_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_admin_user)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy.config_data = json.loads(policy.config_data)
    return policy

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
