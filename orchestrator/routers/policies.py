from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, database

router = APIRouter(
    prefix="/policies",
    tags=["policies"]
)

from ..auth import get_current_active_user

@router.post("/", response_model=schemas.Policy)
def create_policy(
    policy: schemas.PolicyCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_policy = db.query(models.Policy).filter(models.Policy.name == policy.name).first()
    if db_policy:
        raise HTTPException(status_code=400, detail="Policy with this name already exists")
    
    new_policy = models.Policy(**policy.model_dump())
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)
    return new_policy

@router.get("/", response_model=List[schemas.Policy])
def read_policies(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    policies = db.query(models.Policy).offset(skip).limit(limit).all()
    return policies

@router.get("/{policy_id}", response_model=schemas.Policy)
def read_policy(policy_id: int, db: Session = Depends(database.get_db)):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

@router.post("/{policy_id}/assign/{device_id}")
def assign_policy(
    policy_id: int, 
    device_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
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
    current_user: models.User = Depends(get_current_active_user)
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
    current_user: models.User = Depends(get_current_active_user)
):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    # Unset policy_id for all devices using this policy
    db.query(models.Device).filter(models.Device.policy_id == policy_id).update({"policy_id": None})
    
    db.delete(policy)
    db.commit()
    return {"message": "Policy deleted successfully"}
