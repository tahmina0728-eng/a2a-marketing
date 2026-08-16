"""
Compliance Checker — validates the email against regulatory requirements.

Rules implemented:
  CAN-SPAM (US):
    • Physical mailing address must be present in footer.
    • Unsubscribe mechanism must be present and functional.
    • Subject line must not be deceptive (no "Re:" / "Fwd:" if not a reply).

  GDPR (EU):
    • Privacy Policy link must be present.
    • No pre-ticked consent checkboxes (not applicable to static email, skipped).

  CASL (Canada):
    • Sender identification present (brand name in header/footer).
    • Unsubscribe mechanism present.

These are heuristic checks on the rendered HTML — not a substitute for
legal review. All issues are warnings unless explicitly flagged as errors.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ComplianceIssue:
    severity:   str   # "error" | "warning"
    regulation: str   # "CAN-SPAM" | "GDPR" | "CASL"
    code:       str
    message:    str


@dataclass
class ComplianceResult:
    passed: bool
    issues: list[ComplianceIssue] = field(default_factory=list)


class ComplianceChecker:
    """
    Heuristic HTML-based compliance validator.

    Usage:
        checker = ComplianceChecker()
        result  = checker.check(html, slots, brand_name="Haleon")
    """

    def check(
        self,
        html:       str,
        slots:      dict[str, Any] = None,
        brand_name: str = "",
    ) -> ComplianceResult:
        slots  = slots or {}
        issues: list[ComplianceIssue] = []
        lower  = html.lower()

        # ── CAN-SPAM ──────────────────────────────────────────────────────────

        # Unsubscribe link required
        if "unsubscribe" not in lower:
            issues.append(ComplianceIssue(
                severity="error", regulation="CAN-SPAM", code="no_unsubscribe",
                message="No unsubscribe link found. Required by CAN-SPAM.",
            ))

        # Deceptive subject line
        subject = slots.get("subject", "").strip().lower()
        if subject.startswith(("re:", "fwd:", "fw:")):
            issues.append(ComplianceIssue(
                severity="warning", regulation="CAN-SPAM", code="deceptive_subject",
                message="Subject line starts with Re:/Fwd: — may be considered deceptive.",
            ))

        # Physical address (very loose heuristic — checks for street/postcode-like patterns)
        has_address = bool(
            re.search(r'\b\d{1,5}\s+\w[\w\s,]+(?:street|st|avenue|ave|road|rd|lane|ln|blvd)\b', lower)
            or re.search(r'\b[a-z]{1,2}\d{1,2}\s?\d[a-z]{2}\b', lower)   # UK postcode
            or re.search(r'\b\d{5}(?:-\d{4})?\b', lower)                  # US ZIP
        )
        if not has_address:
            issues.append(ComplianceIssue(
                severity="warning", regulation="CAN-SPAM", code="no_physical_address",
                message=(
                    "No physical mailing address detected. "
                    "CAN-SPAM requires a valid postal address in commercial emails."
                ),
            ))

        # ── GDPR ──────────────────────────────────────────────────────────────

        if "privacy" not in lower:
            issues.append(ComplianceIssue(
                severity="warning", regulation="GDPR", code="no_privacy_link",
                message="No privacy policy link detected. Recommended for GDPR compliance.",
            ))

        # ── CASL ──────────────────────────────────────────────────────────────

        # Sender identified
        if brand_name and brand_name.lower() not in lower:
            issues.append(ComplianceIssue(
                severity="warning", regulation="CASL", code="no_sender_id",
                message=(
                    f"Brand name \"{brand_name}\" not found in email. "
                    "CASL requires clear sender identification."
                ),
            ))

        passed = not any(i.severity == "error" for i in issues)
        return ComplianceResult(passed=passed, issues=issues)
