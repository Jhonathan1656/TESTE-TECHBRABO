from itertools import count

from apps.catalog.models import (
    AccessLevel,
    Accommodation,
    ContractType,
    CoverageArea,
    Operator,
    OperatorModality,
    Plan,
    Segmentation,
)

_sequence = count(1)


def create_operator(name: str = "Test Operator", **overrides) -> Operator:
    number = next(_sequence)
    fields = {
        "name": f"{name} {number}" if name == "Test Operator" else name,
        "ans_registration": f"{990000 + number:06d}",
        "modality": OperatorModality.MEDICAL_GROUP,
        "access_level": AccessLevel.MANUAL_CHANNEL,
        "is_fictional": True,
    }
    fields.update(overrides)
    return Operator.objects.create(**fields)


def create_plan(operator: Operator, name: str = "Test Plan", **overrides) -> Plan:
    number = next(_sequence)
    fields = {
        "operator": operator,
        "name": name,
        "product_line": name.split()[0],
        "ans_product_code": f"{990000000 + number:09d}",
        "contract_type": ContractType.SME,
        "accommodation": Accommodation.PRIVATE_ROOM
        if "Apartamento" in name
        else Accommodation.WARD,
        "coverage_area": CoverageArea.STATES_GROUP,
        "segmentation": Segmentation.OUTPATIENT_HOSPITAL_WITH_OBSTETRICS,
    }
    fields.update(overrides)
    return Plan.objects.create(**fields)
