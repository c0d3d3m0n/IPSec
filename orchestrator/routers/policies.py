from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, database

router = APIRouter(
    prefix="/policies",
    tags=["policies"]
)

@router.post("/", response_model=schemas.Policy)
def create_policy(policy: schemas.PolicyCreate, db: Session = Depends(database.get_db)):
    db_policy = db.query(models.Policy).filter(models.Policy.name == policy.name).first()
    if db_policy:
        raise HTTPException(status_code=400, detail="Policy with this name already exists")
    
    new_policy = models.Policy(**policy.model_dump())
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)
    return new_policy

@router.get("/", response_model=List[schemas.Policy])
def read_policies(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    policies = db.query(models.Policy).offset(skip).limit(limit).all()
    return policies

@router.get("/{policy_id}", response_model=schemas.Policy)
def read_policy(policy_id: int, db: Session = Depends(database.get_db)):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

@router.post("/{policy_id}/assign/{device_id}")
def assign_policy(policy_id: int, device_id: int, db: Session = Depends(database.get_db)):
    policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
        
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    device.policy_id = policy.id
    db.commit()
    return {"message": "Policy assigned successfully"}
