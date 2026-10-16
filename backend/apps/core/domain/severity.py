from enum import StrEnum


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


SEVERITY_CHOICES = [(severity.value, severity.value) for severity in Severity]
