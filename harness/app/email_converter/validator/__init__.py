from .html_check import (
    validate_html,
)

from .brand_check import (
    validate_brand,
)

from .compliance import (
    validate_compliance,
)


class ValidationIssue:

    def __init__(
        self,
        code: str,
        message: str,
    ):

        self.code = code
        self.message = message


class ValidationReport:

    def __init__(
        self,
        errors=None,
        warnings=None,
    ):

        self.all_errors = (
            errors
            or []
        )

        self.all_warnings = (
            warnings
            or []
        )

        self.passed = (
            not self.all_errors
        )

    def summary(
        self,
    ):

        status = (
            "Passed"
            if self.passed
            else "Failed"
        )

        return (
            f"{status}: "
            f"{len(self.all_errors)} errors, "
            f"{len(self.all_warnings)} warnings"
        )


def validate(
    html,
    slots=None,
    brand_name="",
    brand_guidelines=None,
):

    errors = []
    warnings = []

    # HTML/internal-content validation

    for code, message in (
        validate_html(html)
    ):

        errors.append(
            ValidationIssue(
                code,
                message,
            )
        )

    # Brand validation

    for code, message in (
        validate_brand(
            html,
            brand_name,
            brand_guidelines,
        )
    ):

        warnings.append(
            ValidationIssue(
                code,
                message,
            )
        )

    # Compliance

    for code, message in (
        validate_compliance(
            html,
            slots or {},
        )
    ):

        warnings.append(
            ValidationIssue(
                code,
                message,
            )
        )

    return ValidationReport(
        errors,
        warnings,
    )