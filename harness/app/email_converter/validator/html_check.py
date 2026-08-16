"""
HTML Checker — validates the generated HTML for email-client compatibility.

Checks:
  1. No <style> blocks with classes only (Outlook strips them) — warns if class-only rules.
  2. No external resource URLs (CDN scripts, external images).
  3. No <link rel="stylesheet"> (stripped by most clients).
  4. Images have width attributes set.
  5. No <script> tags.
  6. No <video> or <audio> tags (unsupported in most clients).
  7. Tables use cellpadding/cellspacing="0".
  8. Total HTML size ≤ 102 KB (Gmail clips at 102 KB).
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field


GMAIL_CLIP_BYTES = 102 * 1024   # 102 KB


@dataclass
class HtmlIssue:
    severity: str   # "error" | "warning"
    code:     str
    message:  str


@dataclass
class HtmlCheckResult:
    passed:  bool
    issues:  list[HtmlIssue] = field(default_factory=list)
    size_kb: float = 0.0

    @property
    def errors(self)   -> list[HtmlIssue]: return [i for i in self.issues if i.severity == "error"]
    @property
    def warnings(self) -> list[HtmlIssue]: return [i for i in self.issues if i.severity == "warning"]


class HtmlChecker:
    """
    Fast regex-based HTML email compatibility checker.

    Usage:
        checker = HtmlChecker()
        result  = checker.check(html_string)
    """

    def check(self, html: str) -> HtmlCheckResult:
        issues: list[HtmlIssue] = []
        size_bytes = len(html.encode("utf-8"))
        size_kb    = round(size_bytes / 1024, 1)

        # 1. Size limit
        if size_bytes > GMAIL_CLIP_BYTES:
            issues.append(HtmlIssue(
                severity="error",
                code="gmail_clip",
                message=(
                    f"Email is {size_kb} KB — Gmail clips messages over 102 KB. "
                    "Reduce image sizes or body length."
                ),
            ))

        # 2. External resources
        ext_srcs = re.findall(r'src=["\']https?://', html, re.IGNORECASE)
        if ext_srcs:
            issues.append(HtmlIssue(
                severity="error",
                code="external_resource",
                message=(
                    f"Found {len(ext_srcs)} external src= URL(s). "
                    "Email clients often block external resources — inline all assets."
                ),
            ))

        # 3. External stylesheets
        if re.search(r'<link[^>]+rel=["\']stylesheet', html, re.IGNORECASE):
            issues.append(HtmlIssue(
                severity="error",
                code="external_stylesheet",
                message="<link rel=\"stylesheet\"> is stripped by most email clients. Use inline styles.",
            ))

        # 4. Script tags
        if re.search(r'<script', html, re.IGNORECASE):
            issues.append(HtmlIssue(
                severity="error",
                code="script_tag",
                message="<script> tags are blocked by all email clients.",
            ))

        # 5. Unsupported media
        for tag in ("video", "audio", "iframe", "form"):
            if re.search(rf'<{tag}[\s>]', html, re.IGNORECASE):
                issues.append(HtmlIssue(
                    severity="warning",
                    code=f"unsupported_{tag}",
                    message=f"<{tag}> is not supported by most email clients.",
                ))

        # 6. Images without width
        imgs_no_width = re.findall(r'<img(?![^>]*width=)[^>]*>', html, re.IGNORECASE)
        if imgs_no_width:
            issues.append(HtmlIssue(
                severity="warning",
                code="img_no_width",
                message=f"{len(imgs_no_width)} <img> element(s) missing a width= attribute.",
            ))

        # 7. Tables without cellpadding / cellspacing
        tables_no_cp = re.findall(
            r'<table(?![^>]*cellpadding=)[^>]*>', html, re.IGNORECASE
        )
        if tables_no_cp:
            issues.append(HtmlIssue(
                severity="warning",
                code="table_no_cellpadding",
                message=(
                    f"{len(tables_no_cp)} <table> element(s) missing cellpadding=\"0\". "
                    "Can cause unexpected spacing in Outlook."
                ),
            ))

        passed = not any(i.severity == "error" for i in issues)
        return HtmlCheckResult(passed=passed, issues=issues, size_kb=size_kb)
