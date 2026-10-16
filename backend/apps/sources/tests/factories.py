from apps.catalog.models import Operator
from apps.sources.models import Source, SourceChannel, TrustLevel


def create_source(operator: Operator, **overrides) -> Source:
    fields = {
        "operator": operator,
        "name": f"{operator.name} portal",
        "channel": SourceChannel.OPERATOR_PORTAL,
        "trust_level": TrustLevel.OFFICIAL,
        "expected_update_days": 30,
        "tolerance_days": 7,
    }
    fields.update(overrides)
    return Source.objects.create(**fields)
