from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from apps.core.domain.age_bands import parse_age_band


def map_operator_row(row: dict[str, str]) -> dict:
    return {
        "registration": row["REGISTRO_OPERADORA"].zfill(6),
        "cnpj": row.get("CNPJ", ""),
        "corporate_name": row.get("RAZAO_SOCIAL", ""),
        "trade_name": row.get("NOME_FANTASIA", ""),
        "modality": row.get("MODALIDADE", ""),
        "state": row.get("UF", "")[:2],
        "registered_on": parse_iso_date(row.get("DATA_REGISTRO_ANS", "")),
    }


def map_plan_row(row: dict[str, str]) -> dict:
    return {
        "ans_plan_id": int(row["ID_PLANO"]),
        "product_code": row.get("CD_PLANO", ""),
        "name": row.get("NM_PLANO", ""),
        "operator_registration": row["REGISTRO_OPERADORA"].zfill(6),
        "contract_type": row.get("CONTRATACAO", ""),
        "segmentation": row.get("SGMT_ASSISTENCIAL", ""),
        "coverage_area": row.get("ABRANGENCIA_COBERTURA", ""),
        "moderating_factor": row.get("FATOR_MODERADOR", ""),
        "accommodation": row.get("ACOMODACAO_HOSPITALAR", ""),
        "status": row.get("SITUACAO_PLANO", ""),
        "status_date": parse_iso_date(row.get("DT_SITUACAO", "")),
    }


def map_price_band_row(row: dict[str, str]) -> dict | None:
    band = parse_age_band(row.get("FAIXA_ETARIA", ""))
    registered_at = parse_brazilian_date(row.get("DT_NTRP", ""))
    if band is None or registered_at is None:
        return None
    return {
        "ans_plan_id": int(row["ID_PLANO"]),
        "operator_registration": row["CD_OPERADORA"].zfill(6),
        "note_code": int(row["CD_NOTA"]),
        "note_registered_at": registered_at,
        "age_band": int(band),
        "commercial_value": parse_decimal(row["VL_COMERCIAL_MENSALIDADE"]),
        "care_expense": parse_decimal(row.get("VL_DESP_ASSISTENCIAL", "")),
        "min_value": parse_decimal(row["VCM_MINIMO"]),
        "max_value": parse_decimal(row["VCM_MAXIMO"]),
    }


def parse_iso_date(text: str) -> date | None:
    try:
        return date.fromisoformat(text[:10]) if text else None
    except ValueError:
        return None


def parse_brazilian_date(text: str) -> date | None:
    try:
        return datetime.strptime(text[:10], "%d/%m/%Y").date() if text else None
    except ValueError:
        return None


def parse_decimal(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(",", ".")) if text else None
    except InvalidOperation:
        return None
