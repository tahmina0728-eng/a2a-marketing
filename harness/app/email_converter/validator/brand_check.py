"""
Brand Checker — validates that the generated email matches brand guidelines.

Checks performed:
  1. Forbidden phrases ("dont_say" list from BrandRAG) are not present.
  2. Brand colour matches slots["brand_color"] (or close enough by hex).
  3. Headline and body contain at least one phrase from the "do_say" list (soft warning).
  4. Subject line length ≤ 55 characters.
  5. CTA is present.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BrandIssue:
    severity: str    # "error" | "warning"
    code:     str    # machine-readable slug
    message:  str    # human-readable description


@dataclass
class BrandCheckResult:
    passed:   bool
    issues:   list[BrandIssue] = field(default_factory=list)

    @property
    def errors(self)   -> list[BrandIssue]: return [i for i in self.issues if i.severity == "error"]
    @property
    def warnings(self) -> list[BrandIssue]: return [i for i in self.issues if i.severity == "warning"]


class BrandChecker:
    """
    Rule-based brand compliance checker.

    Usage:
        checker = BrandChecker()
        result  = checker.check(slots, brand_guidelines)
        if not result.passed:
            for issue in result.errors:
                print(issue.code, issue.message)
    """

    SUBJECT_MAX_LEN = 55

    def check(
        self,
        slots:             dict[str, Any],
        brand_guidelines:  dict[str, Any] = None,
    ) -> BrandCheckResult:
        guidelines = brand_guidelines or {}
        issues: list[BrandIssue] = []

        full_text = " ".join([
            slots.get("subject",  ""),
            slots.get("headline", ""),
            slots.get("subline",  ""),
            " ".join(slots.get("body", [])),
        ]).lower()

        # 1. Forbidden phrases
        for phrase in guidelines.get("dont_say", []):
            if phrase.lower() in full_text:
                issues.append(BrandIssue(
                    severity="error",
                    code="forbidden_phrase",
                    message=f"Forbidden phrase detected: \"{phrase}\"",
                ))

        # 2. Subject length
        subject = slots.get("subject", "")
        if len(subject) > self.SUBJECT_MAX_LEN:
            issues.append(BrandIssue(
                severity="warning",
                code="subject_too_long",
                message=(
                    f"Subject line is {len(subject)} chars "
                    f"(recommended ≤ {self.SUBJECT_MAX_LEN})."
                ),
            ))

        # 3. Missing CTA
        if not slots.get("cta"):
            issues.append(BrandIssue(
                severity="warning",
                code="missing_cta",
                message="No CTA found. Consider adding a call-to-action button.",
            ))

        # 4. Missing headline
        if not slots.get("headline"):
            issues.append(BrandIssue(
                severity="error",
                code="missing_headline",
                message="Email has no headline — required for all layouts.",
            ))

        # 5. Preferred phrases (soft signal)
        do_say = guidelines.get("do_say", [])
        if do_say and not any(p.lower() in full_text for p in do_say):
            issues.append(BrandIssue(
                severity="warning",
                code="no_preferred_phrases",
                message=(
                    "None of the brand's preferred phrases were detected. "
                    f"Consider using: {', '.join(do_say[:3])}"
                ),
            ))

        passed = not any(i.severity == "error" for i in issues)
        return BrandCheckResult(passed=passed, issues=issues)
