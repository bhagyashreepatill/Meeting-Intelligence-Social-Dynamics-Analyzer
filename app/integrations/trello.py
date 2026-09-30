"""Trello integration for creating cards from accepted meeting action items."""

from typing import Dict, Any, Optional
import httpx
from app.utils.config import settings
from app.utils.logging import logger


class TrelloIntegration:
    """Creates Trello cards on specified boards/lists for confirmed action items."""

    def __init__(self):
        self.api_key = settings.trello_api_key
        self.token = settings.trello_token
        self.list_id = settings.trello_list_id or "demo_list_id"

    def format_card_payload(self, action_item: Dict[str, Any]) -> Dict[str, Any]:
        """Format an action item into standard Trello REST API card payload."""
        task = action_item.get("task", "Meeting Action Item")
        owner = action_item.get("owner", "Unassigned")
        due = action_item.get("due_date", "")
        priority = action_item.get("priority", "Medium")
        evidence = action_item.get("evidence", "")

        desc = (
            f"**Owner:** {owner}\n"
            f"**Priority:** {priority}\n"
            f"**Due Date:** {due}\n\n"
            f"**Transcript Context:**\n> {evidence}"
        )

        payload: Dict[str, Any] = {
            "name": f"[{priority}] {task}",
            "desc": desc,
            "idList": self.list_id
        }
        if due and due != "Unknown":
            payload["due"] = due

        return payload

    async def create_card(self, action_item: Dict[str, Any]) -> Dict[str, Any]:
        """Create Trello card. Operates in simulated demo mode if credentials are not configured."""
        payload = self.format_card_payload(action_item)

        if settings.demo_mode or not (self.api_key and self.token):
            mock_id = f"card_{abs(hash(payload['name'])) % 10000:04d}"
            logger.info("DEMO_MODE: Simulating Trello card creation: %s", mock_id)
            return {
                "status": "success",
                "mode": "demo_simulated",
                "card_id": mock_id,
                "card_url": f"https://trello.com/c/{mock_id}/{payload['name'][:20]}",
                "name": payload["name"]
            }

        try:
            url = "https://api.trello.com/1/cards"
            params = {
                "key": self.api_key,
                "token": self.token,
                **payload
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, params=params)
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "status": "success",
                        "mode": "live",
                        "card_id": data.get("id"),
                        "card_url": data.get("url")
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Trello API error {res.status_code}: {res.text}"
                    }
        except Exception as e:
            logger.error("Trello integration exception: %s", str(e))
            return {"status": "error", "message": f"Connection error: {str(e)}"}
