from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from .. import models, schemas, database
from datetime import datetime

router = APIRouter(
    prefix="/devices",
    tags=["devices"]
)

from ..auth import get_current_active_user

@router.post("/enroll", response_model=schemas.Device)
def enroll_device(device: schemas.DeviceCreate, db: Session = Depends(database.get_db)):
    # 1. Look for pre-registered device with this number and token
    clean_no = device.enrollment_number.strip()
    clean_token = device.enrollment_token.strip()
    
    db_device = db.query(models.Device).filter(
        models.Device.enrollment_number == clean_no,
        models.Device.enrollment_token == clean_token
    ).first()
    
    if not db_device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid enrollment credentials. Please contact your administrator."
        )
    
    if db_device.status == "REVOKED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This enrollment has been revoked."
        )

    # 2. Update device info and activate
    db_device.hostname = device.hostname
    db_device.os_type = device.os_type
    db_device.public_ip = device.public_ip
    db_device.status = "ACTIVE"
    db_device.last_seen = datetime.utcnow()
    
    db.commit()
    db.refresh(db_device)
    return db_device

@router.get("/", response_model=List[schemas.Device])
def read_devices(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    devices = db.query(models.Device).offset(skip).limit(limit).all()
    return devices

@router.post("/register", response_model=schemas.Device)
def register_device(
    device: schemas.DeviceAdminCreate, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Admin endpoint to pre-register a device."""
    existing = db.query(models.Device).filter(models.Device.enrollment_number == device.enrollment_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Enrollment number already exists")
        
    new_device = models.Device(
        enrollment_number=device.enrollment_number,
        enrollment_token=device.enrollment_token,
        status="PENDING"
    )
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return new_device

@router.get("/{device_id}", response_model=schemas.Device)
def read_device(
    device_id: int, 
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.get("/{device_id}/config", response_model=schemas.PolicyResponse)
def get_device_config(device_id: int, db: Session = Depends(database.get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device enrollment is not active")

    if not device.policy:
        # Update last_seen even if no policy, to act as heartbeat
        device.last_seen = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=404, detail="No policy assigned to this device")
        
    # Update last_seen on every config poll (heartbeat)
    device.last_seen = datetime.utcnow()
    db.commit()
    db.refresh(device)
    
    policy = device.policy
    policy.config_data = json.loads(policy.config_data)
    
    return policy
