"""Integrations API router for dispatching confirmed action items to Slack, Jira, and Trello."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import Meeting, ActionItem
from app.schemas.schemas import IntegrationDispatchSchema
from app.integrations.slack import SlackIntegration
from app.integrations.jira import JiraIntegration
from app.integrations.trello import TrelloIntegration

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


def get_confirmed_action_items(meeting_id: int, item_ids: list, db: Session) -> tuple[Meeting, List[ActionItem]]:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    query = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id)
    if item_ids:
        query = query.filter(ActionItem.id.in_(item_ids))
    else:
        # Default: only send confirmed/accepted items! (Feature 20 requirement)
        query = query.filter(ActionItem.status.in_(["Confirmed", "Assigned", "In Progress"]))

    items = query.all()
    if not items:
        raise HTTPException(status_code=400, detail="No accepted or confirmed action items found to dispatch.")
    return meeting, items


@router.post("/slack")
async def dispatch_slack(payload: IntegrationDispatchSchema, db: Session = Depends(get_db)):
    """Dispatch confirmed meeting action items to Slack channel."""
    meeting, items = get_confirmed_action_items(payload.meeting_id, payload.action_item_ids, db)
    
    items_data = [
        {"id": a.id, "task": a.task, "owner": a.owner, "due_date": a.due_date, "priority": a.priority}
        for a in items
    ]

    slack = SlackIntegration()
    result = await slack.send_action_items(meeting.title, items_data)
    
    # Update external reference
    for item in items:
        item.external_reference = f"slack:{result.get('mode', 'live')}"
    db.commit()

    return result


@router.post("/jira")
async def dispatch_jira(payload: IntegrationDispatchSchema, db: Session = Depends(get_db)):
    """Create Jira issues for confirmed meeting action items."""
    meeting, items = get_confirmed_action_items(payload.meeting_id, payload.action_item_ids, db)

    jira = JiraIntegration()
    created_issues = []

    for item in items:
        item_data = {
            "id": item.id,
            "task": item.task,
            "owner": item.owner,
            "due_date": item.due_date,
            "priority": item.priority,
            "evidence": item.evidence or item.task
        }
        res = await jira.create_issue(item_data)
        if res.get("status") == "success":
            item.external_reference = res.get("issue_key")
            created_issues.append(res)

    db.commit()
    return {
        "status": "success",
        "items_processed": len(items),
        "issues": created_issues
    }


@router.post("/trello")
async def dispatch_trello(payload: IntegrationDispatchSchema, db: Session = Depends(get_db)):
    """Create Trello cards for confirmed meeting action items."""
    meeting, items = get_confirmed_action_items(payload.meeting_id, payload.action_item_ids, db)

    trello = TrelloIntegration()
    created_cards = []

    for item in items:
        item_data = {
            "id": item.id,
            "task": item.task,
            "owner": item.owner,
            "due_date": item.due_date,
            "priority": item.priority,
            "evidence": item.evidence or item.task
        }
        res = await trello.create_card(item_data)
        if res.get("status") == "success":
            item.external_reference = res.get("card_id")
            created_cards.append(res)

    db.commit()
    return {
        "status": "success",
        "items_processed": len(items),
        "cards": created_cards
    }
