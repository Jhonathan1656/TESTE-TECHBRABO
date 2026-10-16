import csv
import zipfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from apps.ans_reference.models import AnsDataset
from apps.core.domain.age_bands import AgeBand
from apps.core.domain.money import CENT
from apps.demo.scenario import calculate_price

# Column layouts of the real ANS open-data files (verified against dadosabertos.ans.gov.br).
OPERATORS_HEADER = (
    "REGISTRO_OPERADORA",
    "CNPJ",
    "RAZAO_SOCIAL",
    "NOME_FANTASIA",
    "MODALIDADE",
    "LOGRADOURO",
    "NUMERO",
    "COMPLEMENTO",
    "BAIRRO",
    "CIDADE",
    "UF",
    "CEP",
    "DDD",
    "TELEFONE",
    "FAX",
    "ENDERECO_ELETRONICO",
    "REPRESENTANTE",
    "CARGO_REPRESENTANTE",
    "REGIAO_DE_COMERCIALIZACAO",
    "DATA_REGISTRO_ANS",
)
PLANS_HEADER = (
    "ID_PLANO",
    "CD_PLANO",
    "NM_PLANO",
    "REGISTRO_OPERADORA",
    "RAZAO_SOCIAL",
    "GR_MODALIDADE",
    "PORTE_OPERADORA",
    "VIGENCIA_PLANO",
    "CONTRATACAO",
    "GR_CONTRATACAO",
    "SGMT_ASSISTENCIAL",
    "GR_SGMT_ASSISTENCIAL",
    "LG_ODONTOLOGICO",
    "OBSTETRICIA",
    "COBERTURA",
    "TIPO_FINANCIAMENTO",
    "ABRANGENCIA_COBERTURA",
    "ID_GEO_COBERTURA",
    "FATOR_MODERADOR",
    "ACOMODACAO_HOSPITALAR",
    "LIVRE_ESCOLHA",
    "SITUACAO_PLANO",
    "DT_SITUACAO",
    "DT_REGISTRO_PLANO",
    "DT_ATUALIZACAO",
)
PRICE_BANDS_HEADER = (
    "CD_OPERADORA",
    "ID_PLANO",
    "CD_NOTA",
    "DT_NTRP",
    "ID_ABRG",
    "FAIXA_ETARIA",
    "VL_COMERCIAL_MENSALIDADE",
    "VL_DESP_ASSISTENCIAL",
    "VCM_MINIMO",
    "VCM_MAXIMO",
    "DT_ATUALIZACAO",
)

# ANS limits commercialization to VCM -30%/+30% (floor: expected care cost per beneficiary).
_VCM_LOWER_FACTOR = Decimal("0.70")
_VCM_UPPER_FACTOR = Decimal("1.30")
_CARE_EXPENSE_SHARE = Decimal("0.45")
_PLAN_REGISTERED_ON = date(2024, 5, 10)
_OPERATOR_REGISTERED_ON = date(2010, 3, 15)
_FIRST_NOTE_CODE = 55000


def write_ans_samples(scenario: dict, today: date, folder: Path) -> dict[AnsDataset, Path]:
    operators_path = folder / "Relatorio_cadop.csv"
    plans_path = folder / "pda-008-caracteristicas_produtos_saude_suplementar.csv"
    bands_zip_path = folder / "nota_tecnica_vcm_faixa_etaria.zip"
    write_csv(operators_path, OPERATORS_HEADER, build_operator_rows(scenario))
    write_csv(plans_path, PLANS_HEADER, build_plan_rows(scenario, today))
    bands_csv_path = folder / f"NOTA_TECNICA_VCM_FAIXA_ETARIA_{today.year}.csv"
    write_csv(bands_csv_path, PRICE_BANDS_HEADER, build_price_band_rows(scenario, today))
    with zipfile.ZipFile(bands_zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(bands_csv_path, bands_csv_path.name)
    return {
        AnsDataset.OPERATORS: operators_path,
        AnsDataset.PLANS: plans_path,
        AnsDataset.PRICE_BANDS: bands_zip_path,
    }


def build_operator_rows(scenario: dict) -> list[list[str]]:
    return [
        [
            operator["ans_registration"],
            operator["cnpj"],
            operator["corporate_name"],
            operator["name"],
            operator["ans_modality"],
            "",
            "",
            "",
            "",
            "",
            operator["state"],
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "4",
            _OPERATOR_REGISTERED_ON.isoformat(),
        ]
        for operator in scenario["operators"]
    ]


def build_plan_rows(scenario: dict, today: date) -> list[list[str]]:
    vocabulary = scenario["ans_vocabulary"]
    rows = []
    for operator in scenario["operators"]:
        for plan in operator["plans"]:
            status_date = (
                today - timedelta(days=plan["ans_status_days_ago"])
                if "ans_status_days_ago" in plan
                else _PLAN_REGISTERED_ON
            )
            rows.append(
                [
                    str(plan["ans_plan_id"]),
                    plan["ans_product_code"],
                    plan["name"].upper(),
                    operator["ans_registration"],
                    operator["corporate_name"],
                    operator["ans_modality"],
                    vocabulary["operator_size"],
                    "P",
                    plan["contract_label"],
                    plan["contract_label"],
                    vocabulary["segmentation"],
                    vocabulary["segmentation_group"],
                    "0",
                    vocabulary["obstetrics"],
                    vocabulary["coverage"],
                    vocabulary["financing"],
                    vocabulary["coverage_area"][plan["coverage_area"]],
                    "",
                    vocabulary["moderating_factor"][str(plan["has_coparticipation"]).lower()],
                    vocabulary["accommodation"][plan["accommodation"]],
                    vocabulary["free_choice"],
                    plan.get("ans_status", vocabulary["active_status"]),
                    status_date.isoformat(),
                    _PLAN_REGISTERED_ON.isoformat(),
                    today.isoformat(),
                ]
            )
    return rows


def build_price_band_rows(scenario: dict, today: date) -> list[list[str]]:
    note_factor = scenario["ans_note_factor"]
    abrangency = scenario["ans_vocabulary"]["abrangency"]
    rows = []
    note_code = _FIRST_NOTE_CODE
    for operator in scenario["operators"]:
        for plan in operator["plans"]:
            note_code += 1
            for band, label in zip(AgeBand, scenario["band_labels"], strict=True):
                commercial = calculate_price(plan["base_price"], band, note_factor)
                care_expense = (commercial * _CARE_EXPENSE_SHARE).quantize(CENT)
                minimum = max((commercial * _VCM_LOWER_FACTOR).quantize(CENT), care_expense)
                maximum = (commercial * _VCM_UPPER_FACTOR).quantize(CENT)
                rows.append(
                    [
                        operator["ans_registration"],
                        str(plan["ans_plan_id"]),
                        str(note_code),
                        _PLAN_REGISTERED_ON.strftime("%d/%m/%Y"),
                        abrangency,
                        label,
                        str(commercial),
                        str(care_expense),
                        str(minimum),
                        str(maximum),
                        today.strftime("%d/%m/%Y"),
                    ]
                )
    return rows


def write_csv(path: Path, header: tuple[str, ...], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(header)
        writer.writerows(rows)
