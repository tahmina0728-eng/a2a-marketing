"""
mailchimp_client.py — Mailchimp Marketing API v3 integration.

Handles: audiences, campaign creation, content upload, send, and reports.
API key format: <key>-<server>  e.g.  abc123def456-us1
"""
import os
import requests
import structlog

logger = structlog.get_logger()


def _api_key() -> str:
    key = os.getenv("MAILCHIMP_API_KEY", "")
    if not key:
        raise ValueError("MAILCHIMP_API_KEY not set in environment")
    return key


def _server() -> str:
    """Extract data-centre prefix from the API key (e.g. 'us1')."""
    key = _api_key()
    if "-" in key:
        return key.split("-")[-1]
    return os.getenv("MAILCHIMP_SERVER", "us1")


def _base() -> str:
    return f"https://{_server()}.api.mailchimp.com/3.0"


def _headers() -> dict:
    import base64
    token = base64.b64encode(f"anystring:{_api_key()}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def _get(path: str, params: dict = None) -> dict:
    r = requests.get(f"{_base()}{path}", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def _post(path: str, body: dict) -> dict:
    r = requests.post(f"{_base()}{path}", headers=_headers(), json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def _put(path: str, body: dict) -> dict:
    r = requests.put(f"{_base()}{path}", headers=_headers(), json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def _patch(path: str, body: dict) -> dict:
    r = requests.patch(f"{_base()}{path}", headers=_headers(), json=body, timeout=15)
    r.raise_for_status()
    return r.json()


# ── Account ────────────────────────────────────────────────────

def ping() -> dict:
    """Verify API key and return account info."""
    return _get("/")


# ── Audiences (Lists) ──────────────────────────────────────────

def list_audiences(count: int = 20) -> list[dict]:
    """Return all audiences / contact lists."""
    data = _get("/lists", params={"count": count, "fields": "lists.id,lists.name,lists.stats"})
    return [
        {
            "id":           a["id"],
            "name":         a["name"],
            "member_count": a.get("stats", {}).get("member_count", 0),
        }
        for a in data.get("lists", [])
    ]


def get_audience(list_id: str) -> dict:
    return _get(f"/lists/{list_id}")


def list_segments(list_id: str) -> list[dict]:
    """Return saved segments for an audience."""
    data = _get(f"/lists/{list_id}/segments", params={"count": 50})
    return [{"id": s["id"], "name": s["name"], "member_count": s.get("member_count", 0)}
            for s in data.get("segments", [])]


# ── Templates ─────────────────────────────────────────────────

def list_templates(type_: str = "user") -> list[dict]:
    """Return saved templates (user-created and base)."""
    data = _get("/templates", params={"type": type_, "count": 50})
    return [{"id": t["id"], "name": t["name"], "thumbnail": t.get("thumbnail", "")}
            for t in data.get("templates", [])]


def create_template(name: str, html: str) -> dict:
    """Upload an AI-generated HTML email as a Mailchimp template."""
    result = _post("/templates", {"name": name, "html": html})
    logger.info("mailchimp_template_created", name=name, template_id=result.get("id"))
    return {"id": result["id"], "name": result["name"]}


def update_template(template_id: int, name: str, html: str) -> dict:
    result = _patch(f"/templates/{template_id}", {"name": name, "html": html})
    return {"id": result["id"], "name": result["name"]}


def delete_template(template_id: int) -> None:
    requests.delete(f"{_base()}/templates/{template_id}", headers=_headers(), timeout=10)


# ── Campaigns ─────────────────────────────────────────────────

def _account_email() -> str:
    """Return the verified email from the connected Mailchimp account."""
    try:
        info = ping()
        return info.get("email", "")
    except Exception:
        return ""


def create_campaign(
    list_id:   str,
    subject:   str,
    from_name: str,
    reply_to:  str,
    preview_text: str = "",
    title:     str = "",
) -> dict:
    """Create a regular email campaign and return its ID."""
    # reply_to must be a verified email — fall back to account email if empty
    effective_reply_to = reply_to or _account_email()
    body = {
        "type": "regular",
        "recipients": {"list_id": list_id},
        "settings": {
            "subject_line": subject,
            "preview_text": preview_text,
            "title":        title or subject[:50],
            "from_name":    from_name,
            "reply_to":     effective_reply_to,
        },
    }
    result = _post("/campaigns", body)
    logger.info("mailchimp_campaign_created", campaign_id=result["id"], subject=subject)
    return {"id": result["id"], "status": result["status"], "web_id": result.get("web_id")}


def set_campaign_content(campaign_id: str, html: str, plain_text: str = "") -> dict:
    """Upload HTML (and optional plain-text) content to a draft campaign."""
    body: dict = {"html": html}
    if plain_text:
        body["plain_text"] = plain_text
    result = _put(f"/campaigns/{campaign_id}/content", body)
    return {"campaign_id": campaign_id, "archive_html": bool(result.get("archive_html"))}


def schedule_campaign(campaign_id: str, schedule_time: str) -> dict:
    """Schedule a campaign for future send (ISO 8601 UTC, e.g. '2026-07-10T09:00:00+00:00')."""
    result = _post(f"/campaigns/{campaign_id}/actions/schedule", {"schedule_time": schedule_time})
    return result


def send_campaign(campaign_id: str) -> dict:
    """Send a campaign immediately."""
    requests.post(
        f"{_base()}/campaigns/{campaign_id}/actions/send",
        headers=_headers(), timeout=15,
    ).raise_for_status()
    logger.info("mailchimp_campaign_sent", campaign_id=campaign_id)
    return {"campaign_id": campaign_id, "status": "sent"}


def get_campaign(campaign_id: str) -> dict:
    return _get(f"/campaigns/{campaign_id}")


def list_campaigns(count: int = 20) -> list[dict]:
    data = _get("/campaigns", params={"count": count, "status": "sent,sending,schedule,paused",
                                       "fields": "campaigns.id,campaigns.settings,campaigns.status,campaigns.send_time"})
    return [
        {
            "id":        c["id"],
            "title":     c.get("settings", {}).get("title", ""),
            "subject":   c.get("settings", {}).get("subject_line", ""),
            "status":    c["status"],
            "send_time": c.get("send_time", ""),
        }
        for c in data.get("campaigns", [])
    ]


# ── Reports / KPIs ─────────────────────────────────────────────

def get_report(campaign_id: str) -> dict:
    """Return KPI report for a sent campaign."""
    try:
        r = _get(f"/reports/{campaign_id}")
        return {
            "campaign_id":     campaign_id,
            "subject":         r.get("subject_line", ""),
            "emails_sent":     r.get("emails_sent", 0),
            "open_rate":       round(r.get("opens", {}).get("open_rate", 0) * 100, 1),
            "click_rate":      round(r.get("clicks", {}).get("click_rate", 0) * 100, 1),
            "unique_opens":    r.get("opens", {}).get("unique_opens", 0),
            "unique_clicks":   r.get("clicks", {}).get("unique_clicks", 0),
            "unsubscribed":    r.get("unsubscribed", 0),
            "bounces_hard":    r.get("bounces", {}).get("hard_bounces", 0),
            "bounces_soft":    r.get("bounces", {}).get("soft_bounces", 0),
            "send_time":       r.get("send_time", ""),
        }
    except Exception as e:
        logger.warning("mailchimp_report_failed", campaign_id=campaign_id, error=str(e))
        return {"campaign_id": campaign_id, "error": str(e)}


def list_reports(count: int = 10) -> list[dict]:
    data = _get("/reports", params={"count": count,
                                     "fields": "reports.id,reports.subject_line,reports.emails_sent,reports.opens,reports.clicks,reports.send_time"})
    return [
        {
            "id":          r["id"],
            "subject":     r.get("subject_line", ""),
            "emails_sent": r.get("emails_sent", 0),
            "open_rate":   round(r.get("opens", {}).get("open_rate", 0) * 100, 1),
            "click_rate":  round(r.get("clicks", {}).get("click_rate", 0) * 100, 1),
            "send_time":   r.get("send_time", ""),
        }
        for r in data.get("reports", [])
    ]


# ── High-level helper ──────────────────────────────────────────

def create_and_send(
    list_id:      str,
    subject:      str,
    html:         str,
    from_name:    str,
    reply_to:     str,
    preview_text: str = "",
    schedule_time: str = "",   # if empty → send immediately
) -> dict:
    """
    Full flow: create campaign → upload HTML → send (or schedule).
    Returns campaign id + status.
    """
    campaign = create_campaign(
        list_id=list_id, subject=subject,
        from_name=from_name, reply_to=reply_to,
        preview_text=preview_text,
    )
    cid = campaign["id"]
    set_campaign_content(cid, html)
    if schedule_time:
        schedule_campaign(cid, schedule_time)
        return {"campaign_id": cid, "status": "scheduled", "schedule_time": schedule_time}
    send_campaign(cid)
    return {"campaign_id": cid, "status": "sent"}
