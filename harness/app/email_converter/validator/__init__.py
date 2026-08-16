"""
Email Validator — runs brand, HTML compatibility, and compliance checks.

Returns a combined ValidationReport with all issues ranked by severity.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .brand_check  import BrandChecker,      BrandCheckResult
from .html_check   import HtmlChecker,       HtmlCheckResult
from .compliance   import ComplianceChecker, ComplianceResult


@dataclass
class ValidationReport:
    passed:     bool
    brand:      BrandCheckResult
    html:       HtmlCheckResult
    compliance: ComplianceResult
    size_kb:    float = 0.0

    @property
    def all_errors(self) -> list:
        return (
            list(self.brand.errors)
            + list(self.html.errors)
            + [i for i in self.compliance.issues if i.severity == "error"]
        )

    @property
    def all_warnings(self) -> list:
        return (
            list(self.brand.warnings)
            + list(self.html.warnings)
            + [i for i in self.compliance.issues if i.severity == "warning"]
        )

    def summary(self) -> str:
        e = len(self.all_errors)
        w = len(self.all_warnings)
        kb = self.size_kb
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {e} error(s), {w} warning(s) — {kb} KB"


def validate(
    html:              str,
    slots:             dict[str, Any] = None,
    brand_name:        str = "",
    brand_guidelines:  dict[str, Any] = None,
) -> ValidationReport:
    """
    Run all three validators and return a combined ValidationReport.

    Args:
        html             : rendered HTML email string
        slots            : ContentSlots dict (for brand/compliance checks)
        brand_name       : display brand name
        brand_guidelines : dict from BrandRAG.search() — tone, do/dont_say, etc.
    """
    slots = slots or {}

    brand_result      = BrandChecker().check(slots, brand_guidelines or {})
    html_result       = HtmlChecker().check(html)
    compliance_result = ComplianceChecker().check(html, slots, brand_name)

    passed = brand_result.passed and html_result.passed and compliance_result.passed

    return ValidationReport(
        passed     = passed,
        brand      = brand_result,
        html       = html_result,
        compliance = compliance_result,
        size_kb    = html_result.size_kb,
    )


__all__ = ["validate", "ValidationReport"]
