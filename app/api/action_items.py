"""Action items API router for review, edits, lifecycle transitions, and confirmation."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.action_item import ActionItem
from app.schemas.schemas import ActionItemSchema, ActionItemUpdateSchema

router = APIRouter(tags=["action_items"])


@router.get("/api/meetings/{meeting_id}/action-items", response_model=List[ActionItemSchema])
def get_meeting_action_items(meeting_id: int, db: Session = Depends(get_db)):
    """List all action items for a given meeting."""
    items = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
    return items


@router.post("/api/action-items/{item_id}/accept", response_model=ActionItemSchema)
def accept_action_item(item_id: int, db: Session = Depends(get_db)):
    """
    Accept/confirm an AI-extracted action item.
    Feature 20: Action Item Confirmation.
    """
    item = db.query(ActionItem).filter(ActionItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    item.status = "Confirmed"
    db.commit()
    db.refresh(item)
    return item


@router.post("/api/action-items/{item_id}/reject", response_model=ActionItemSchema)
def reject_action_item(item_id: int, db: Session = Depends(get_db)):
    """
    Reject an incorrectly extracted action item.
    Feature 20: Action Item Confirmation.
    """
    item = db.query(ActionItem).filter(ActionItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    item.status = "Rejected"
    db.commit()
    db.refresh(item)
    return item


@router.put("/api/action-items/{item_id}", response_model=ActionItemSchema)
def update_action_item(
    item_id: int,
    payload: ActionItemUpdateSchema,
    db: Session = Depends(get_db)
):
    """
    Edit task, owner, due date, priority, or lifecycle status.
    Feature 19 & 20: Action Item Lifecycle & Manual Edits.
    """
    item = db.query(ActionItem).filter(ActionItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    if payload.task is not None:
        item.task = payload.task.strip()
    if payload.owner is not None:
        item.owner = payload.owner.strip()
    if payload.due_date is not None:
        item.due_date = payload.due_date.strip()
    if payload.priority is not None:
        item.priority = payload.priority.strip()
    if payload.status is not None:
        item.status = payload.status.strip()

    db.commit()
    db.refresh(item)
    return item
