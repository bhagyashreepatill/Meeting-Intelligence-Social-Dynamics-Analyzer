"""Jira integration for creating issues from accepted meeting action items."""

from typing import Dict, Any, Optional
import httpx
from app.utils.config import settings
from app.utils.logging import logger


class JiraIntegration:
    """Creates Jira issues for confirmed action items."""

    def __init__(self):
        self.server_url = settings.jira_server_url
        self.api_token = settings.jira_api_token
        self.user_email = settings.jira_user_email
        self.project_key = settings.jira_project_key

    def format_issue_payload(self, action_item: Dict[str, Any]) -> Dict[str, Any]:
        """Format an action item into standard Jira REST API issue creation payload."""
        task = action_item.get("task", "Meeting Action Item")
        owner = action_item.get("owner", "Unassigned")
        due = action_item.get("due_date", "")
        priority = action_item.get("priority", "Medium")
        evidence = action_item.get("evidence", "")

        jira_priority_map = {"High": "High", "Medium": "Medium", "Low": "Low"}

        desc = (
            f"Action item extracted from meeting intelligence analysis.\n\n"
            f"*Assigned Owner:* {owner}\n"
            f"*Due Date:* {due}\n"
            f"*Priority:* {priority}\n\n"
            f"*Transcript Context:*\n> {evidence}\n"
        )

        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": task,
                "description": desc,
                "issuetype": {"name": "Task"},
                "priority": {"name": jira_priority_map.get(priority, "Medium")}
            }
        }
        if due and due != "Unknown":
            payload["fields"]["duedate"] = due

        return payload

    async def create_issue(self, action_item: Dict[str, Any]) -> Dict[str, Any]:
        """Create Jira issue. Operates in simulated demo mode if credentials are not configured."""
        payload = self.format_issue_payload(action_item)

        if settings.demo_mode or not (self.server_url and self.api_token and self.user_email):
            mock_id = 1042 + action_item.get("id", 1)
            issue_key = f"{self.project_key}-{mock_id}"
            logger.info("DEMO_MODE: Simulating Jira issue creation: %s", issue_key)
            return {
                "status": "success",
                "mode": "demo_simulated",
                "issue_key": issue_key,
                "issue_url": f"https://example.atlassian.net/browse/{issue_key}",
                "summary": payload["fields"]["summary"]
            }

        try:
            url = f"{self.server_url.rstrip('/')}/rest/api/2/issue"
            auth = (self.user_email, self.api_token)
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload, auth=auth)
                if res.status_code in (200, 201):
                    data = res.json()
                    key = data.get("key", f"{self.project_key}-NEW")
                    return {
                        "status": "success",
                        "mode": "live",
                        "issue_key": key,
                        "issue_url": f"{self.server_url.rstrip('/')}/browse/{key}"
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Jira API error {res.status_code}: {res.text}"
                    }
        except Exception as e:
            logger.error("Jira integration exception: %s", str(e))
            return {"status": "error", "message": f"Connection error: {str(e)}"}
