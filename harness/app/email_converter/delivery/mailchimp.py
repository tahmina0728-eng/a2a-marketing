"""
Mailchimp / Eloqua Delivery — sends the generated email via an ESP.

Mailchimp:
  Uses the Mailchimp Marketing API v3.
  Requires: MAILCHIMP_API_KEY and MAILCHIMP_SERVER_PREFIX env vars
            (e.g. api_key="abc123-us6", server="us6").

Eloqua (Oracle Marketing Cloud):
  Uses the Eloqua REST API.
  Requires: ELOQUA_COMPANY, ELOQUA_USERNAME, ELOQUA_PASSWORD env vars.

Wire-up:
  pip install mailchimp-marketing
  Set the env vars above, then call:
    client = MailchimpClient()
    campaign_id = await client.create_campaign(subject, html, list_id="abc123")
    await client.send(campaign_id)
"""
from __future__ import annotations
import os
from typing import Any


class MailchimpClient:
    """
    Thin async wrapper around the Mailchimp Marketing API.

    Usage:
        mc = MailchimpClient(api_key="...", server="us6")
        campaign_id = await mc.create_campaign(
            subject   = "Our New Campaign",
            html      = "<html>…</html>",
            list_id   = "abc123def",
            from_name = "Haleon",
            reply_to  = "marketing@haleon.com",
        )
        await mc.send(campaign_id)
    """

    def __init__(
        self,
        api_key: str = "",
        server:  str = "",
    ):
        self._api_key = api_key or os.getenv("MAILCHIMP_API_KEY", "")
        self._server  = server  or os.getenv("MAILCHIMP_SERVER_PREFIX", "us1")

    def _client(self):
        try:
            import mailchimp_marketing as mc
            client = mc.Client()
            client.set_config({"api_key": self._api_key, "server": self._server})
            return client
        except ImportError:
            raise RuntimeError(
                "mailchimp-marketing is required. Install: pip install mailchimp-marketing"
            )

    async def create_campaign(
        self,
        subject:   str,
        html:      str,
        list_id:   str,
        from_name: str = "CampaignOS",
        reply_to:  str = "",
    ) -> str:
        """Create a Mailchimp campaign and upload HTML. Returns campaign_id."""
        client   = self._client()
        campaign = client.campaigns.create({
            "type": "regular",
            "recipients": {"list_id": list_id},
            "settings": {
                "subject_line": subject,
                "from_name":    from_name,
                "reply_to":     reply_to,
            },
        })
        campaign_id = campaign["id"]
        client.campaigns.set_content(campaign_id, {"html": html})
        return campaign_id

    async def send(self, campaign_id: str) -> dict[str, Any]:
        """Immediately send a campaign. Returns the Mailchimp response dict."""
        client = self._client()
        return client.campaigns.send(campaign_id)

    async def schedule(self, campaign_id: str, send_time: str) -> dict[str, Any]:
        """Schedule a campaign. send_time: ISO 8601 UTC string."""
        client = self._client()
        return client.campaigns.schedule(campaign_id, {"schedule_time": send_time})


class EloquaClient:
    """
    Stub for Oracle Eloqua / Marketing Cloud delivery.
    Implement when ELOQUA_COMPANY / ELOQUA_USERNAME / ELOQUA_PASSWORD are available.
    """

    def __init__(self):
        self._company  = os.getenv("ELOQUA_COMPANY",  "")
        self._username = os.getenv("ELOQUA_USERNAME", "")
        self._password = os.getenv("ELOQUA_PASSWORD", "")

    async def create_email(self, subject: str, html: str, folder_id: int = 0) -> int:
        """Create an Eloqua Email asset. Returns the Eloqua email ID."""
        raise NotImplementedError(
            "EloquaClient.create_email not yet implemented. "
            "See https://docs.oracle.com/en/cloud/saas/marketing/eloqua-rest-api/"
        )

    async def send_to_segment(self, email_id: int, segment_id: int) -> dict:
        raise NotImplementedError("EloquaClient.send_to_segment not yet implemented.")
