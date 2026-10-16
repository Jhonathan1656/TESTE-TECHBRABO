from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from apps.core.models import PublicModel


class OperatorModality(models.TextChoices):
    MEDICAL_GROUP = "medical_group", "Medical group"
    MEDICAL_COOPERATIVE = "medical_cooperative", "Medical cooperative"
    INSURER = "insurer", "Health insurer"
    SELF_MANAGED = "self_managed", "Self-managed"
    PHILANTHROPY = "philanthropy", "Philanthropy"


class AccessLevel(models.TextChoices):
    AUTOMATED = "automated", "Automated feed or portal"
    MANUAL_CHANNEL = "manual_channel", "Manual channel"
    CONTACT_DEPENDENT = "contact_dependent", "Depends on personal contacts"
    NO_ACCESS = "no_access", "No direct access"


class ContractType(models.TextChoices):
    INDIVIDUAL = "individual", "Individual or family"
    SME = "sme", "Small business"
    CORPORATE = "corporate", "Corporate"
    ADHESION = "adhesion", "Collective by adhesion"


class Accommodation(models.TextChoices):
    WARD = "ward", "Ward"
    PRIVATE_ROOM = "private_room", "Private room"
    NOT_APPLICABLE = "not_applicable", "Not applicable"


class CoverageArea(models.TextChoices):
    MUNICIPAL = "municipal", "Municipal"
    MUNICIPALITIES_GROUP = "municipalities_group", "Group of municipalities"
    STATE = "state", "State"
    STATES_GROUP = "states_group", "Group of states"
    NATIONAL = "national", "National"


class Segmentation(models.TextChoices):
    OUTPATIENT = "outpatient", "Outpatient"
    HOSPITAL_WITH_OBSTETRICS = "hospital_with_obstetrics", "Hospital with obstetrics"
    HOSPITAL_WITHOUT_OBSTETRICS = "hospital_without_obstetrics", "Hospital without obstetrics"
    OUTPATIENT_HOSPITAL_WITH_OBSTETRICS = (
        "outpatient_hospital_with_obstetrics",
        "Outpatient + hospital with obstetrics",
    )
    OUTPATIENT_HOSPITAL_WITHOUT_OBSTETRICS = (
        "outpatient_hospital_without_obstetrics",
        "Outpatient + hospital without obstetrics",
    )
    REFERENCE = "reference", "Reference plan"


class Operator(PublicModel):
    name = models.CharField(max_length=140)
    ans_registration = models.CharField(
        max_length=6, unique=True, validators=[RegexValidator(r"^\d{6}$")]
    )
    cnpj = models.CharField(max_length=14, blank=True)
    modality = models.CharField(max_length=32, choices=OperatorModality.choices)
    access_level = models.CharField(max_length=32, choices=AccessLevel.choices)
    is_fictional = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Plan(PublicModel):
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT, related_name="plans")
    name = models.CharField(max_length=140)
    product_line = models.CharField(max_length=60)
    ans_product_code = models.CharField(
        max_length=9, blank=True, validators=[RegexValidator(r"^\d{9}$")]
    )
    contract_type = models.CharField(max_length=20, choices=ContractType.choices)
    accommodation = models.CharField(max_length=20, choices=Accommodation.choices)
    coverage_area = models.CharField(max_length=30, choices=CoverageArea.choices)
    segmentation = models.CharField(max_length=50, choices=Segmentation.choices)
    has_coparticipation = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["operator__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["operator", "name"], name="plan_unique_name_per_operator"
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def formatted_ans_code(self) -> str:
        code = self.ans_product_code
        if len(code) != 9:
            return code
        return f"{code[:3]}.{code[3:6]}/{code[6:8]}-{code[8]}"


class AliasOrigin(models.TextChoices):
    CATALOG = "catalog", "Catalog"
    REVIEW = "review", "Learned from review"


class PlanAlias(models.Model):
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, related_name="plan_aliases")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="aliases")
    normalized_label = models.CharField(max_length=200)
    origin = models.CharField(max_length=10, choices=AliasOrigin.choices)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["operator", "normalized_label"],
                name="plan_alias_unique_label_per_operator",
            ),
        ]

    def __str__(self) -> str:
        return self.normalized_label
