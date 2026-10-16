from datetime import date

import pytest

from apps.ingestion.extraction.metadata_detector import (
    detect_metadata,
    detect_operator_registrations,
)


@pytest.mark.parametrize(
    ("text", "expected_from", "expected_until"),
    [
        ("Vigência: 01/11/2026", date(2026, 11, 1), None),
        ("VIGÊNCIA DA TABELA 01/11/2026 a 31/10/2027", date(2026, 11, 1), date(2027, 10, 31)),
        ("Valores válidos a partir de 01/12/2026.", date(2026, 12, 1), None),
        ("Tabela vigente a partir de 01/03/2026", date(2026, 3, 1), None),
        ("Sem data nenhuma", None, None),
        ("Vigência: 31/02/2026", None, None),
    ],
)
def test_detect_metadata_finds_effective_period(text, expected_from, expected_until):
    metadata = detect_metadata(text)

    assert (metadata.effective_from, metadata.effective_until) == (expected_from, expected_until)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Tabela PME\nRegião: São Paulo – Capital e Grande SP\nVigência: 01/11/2026",
            "São Paulo – Capital e Grande SP",
        ),
        ("REGIÃO DE COMERCIALIZAÇÃO - Baixada Santista", "Baixada Santista"),
        ("Região: Rio de Janeiro | Individual", "Rio de Janeiro"),
        ("Regional Sul sem marcador", None),
    ],
)
def test_detect_metadata_finds_region_line(text, expected):
    assert detect_metadata(text).region == expected


def test_detect_operator_registrations_reads_ans_number():
    text = "Operadora fictícia — Registro ANS nº 900011 — CNPJ 00.000.000/0001-91"

    assert detect_operator_registrations(text) == {"900011"}
