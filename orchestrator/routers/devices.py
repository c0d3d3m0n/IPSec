from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, database
from datetime import datetime

router = APIRouter(
    prefix="/devices",
    tags=["devices"]
)

@router.post("/enroll", response_model=schemas.Device)
def enroll_device(device: schemas.DeviceCreate, db: Session = Depends(database.get_db)):
    # Check if token is valid (In real app, validate against a pre-generated list)
    # For now, we just check if a device with this token already exists, if so return it
    
    db_device = db.query(models.Device).filter(models.Device.enrollment_token == device.enrollment_token).first()
    if db_device:
        # Update existing device info
        db_device.hostname = device.hostname
        db_device.os_type = device.os_type
        db_device.public_ip = device.public_ip
        db_device.last_seen = datetime.utcnow()
        db.commit()
        db.refresh(db_device)
        return db_device
    
    # Create new device
    new_device = models.Device(
        hostname=device.hostname,
        os_type=device.os_type,
        public_ip=device.public_ip,
        enrollment_token=device.enrollment_token,
        last_seen=datetime.utcnow()
    )
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return new_device

@router.get("/", response_model=List[schemas.Device])
def read_devices(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    devices = db.query(models.Device).offset(skip).limit(limit).all()
    return devices

@router.get("/{device_id}", response_model=schemas.Device)
def read_device(device_id: int, db: Session = Depends(database.get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.get("/{device_id}/config", response_model=schemas.Policy)
def get_device_config(device_id: int, db: Session = Depends(database.get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if not device.policy:
        raise HTTPException(status_code=404, detail="No policy assigned to this device")
        
    return device.policy
