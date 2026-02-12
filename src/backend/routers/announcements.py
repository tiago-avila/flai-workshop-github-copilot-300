"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_announcements() -> List[Dict[str, Any]]:
    """
    Get all active announcements (those within their date range)
    """
    current_time = datetime.utcnow().isoformat() + "Z"
    
    announcements = []
    for announcement in announcements_collection.find():
        # Convert ObjectId to string for JSON serialization
        announcement["id"] = str(announcement.pop("_id"))
        
        # Check if announcement is currently active
        start_date = announcement.get("start_date")
        expiration_date = announcement.get("expiration_date")
        
        # Include if no start date or current time is after start date
        # AND current time is before expiration date
        is_active = (not start_date or start_date <= current_time) and \
                   (expiration_date and current_time <= expiration_date)
        
        if is_active:
            announcements.append(announcement)
    
    # Sort by creation date, newest first
    announcements.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return announcements


@router.get("/all", response_model=List[Dict[str, Any]])
def get_all_announcements() -> List[Dict[str, Any]]:
    """
    Get all announcements regardless of date range (for management interface)
    """
    announcements = []
    for announcement in announcements_collection.find():
        # Convert ObjectId to string for JSON serialization
        announcement["id"] = str(announcement.pop("_id"))
        announcements.append(announcement)
    
    # Sort by creation date, newest first
    announcements.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return announcements


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def create_announcement(
    message: str,
    expiration_date: str,
    username: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new announcement
    
    - message: The announcement text
    - expiration_date: ISO 8601 format datetime when announcement expires (required)
    - start_date: ISO 8601 format datetime when announcement becomes active (optional)
    - username: Username of the teacher creating the announcement
    """
    # Verify the user exists and is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
        if start_date:
            st_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            if st_date >= exp_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Start date must be before expiration date"
                )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Create announcement
    announcement = {
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_by": username,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    result = announcements_collection.insert_one(announcement)
    announcement["id"] = str(result.inserted_id)
    announcement.pop("_id", None)
    
    return announcement


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    username: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing announcement
    """
    # Verify the user exists and is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    # Validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
        if start_date:
            st_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            if st_date >= exp_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Start date must be before expiration date"
                )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Update announcement
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    update_data = {
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date
    }
    
    result = announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Return updated announcement
    announcement = announcements_collection.find_one({"_id": obj_id})
    announcement["id"] = str(announcement.pop("_id"))
    
    return announcement


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, str]:
    """
    Delete an announcement
    """
    # Verify the user exists and is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="User not authenticated")
    
    try:
        obj_id = ObjectId(announcement_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
