import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx2

from apps.core.domain.age_bands import AgeBand
from apps.ingestion.extraction.document_content import DocumentContent
from apps.ingestion.extraction.llm_extractor import LlmPriceExtractor, build_llm_extractor
from apps.ingestion.extraction.pipeline import extract_prices

FIXTURE = Path(__file__).parent / "fixtures" / "llm_notice_response.json"
NOTICE = DocumentContent(text="Comunicado: novos valores a partir de 01/12/2026...", tables=())


class FakeMessages:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.requests: list[dict] = []

    def create(self, **request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.response


def build_fake_client(response=None, error=None) -> SimpleNamespace:
    return SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages(response, error)))


def build_response(payload_text: str, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        model="claude-opus-5-5",
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=payload_text),
        ],
    )


def test_extracts_cells_from_recorded_structured_response():
    client = build_fake_client(build_response(FIXTURE.read_text(encoding="utf-8")))
    extractor = LlmPriceExtractor(client=client, model="claude-opus-5-5")

    result = extractor.extract(NOTICE)

    assert result.succeeded
    assert result.method == "llm"
    assert len(result.cells) == 10
    last = result.cells[-1]
    assert (last.age_band, last.raw_text, last.value) == (
        AgeBand.BAND_59_PLUS,
        "R$ 1.103,01",
        Decimal("1103.01"),
    )
    assert result.metadata.region == "Baixada Santista"
    assert result.metadata.effective_from.isoformat() == "2026-12-01"
    assert result.metadata.effective_until is None
    assert result.details == {"model": "claude-opus-5-5"}


def test_request_uses_schema_constrained_output_and_refusal_fallback():
    client = build_fake_client(build_response(FIXTURE.read_text(encoding="utf-8")))

    LlmPriceExtractor(client=client, model="claude-opus-5-5").extract(NOTICE)

    [request] = client.beta.messages.requests
    assert request["model"] == "claude-opus-5-5"
    assert request["output_config"]["format"]["type"] == "json_schema"
    assert request["fallbacks"] == "default"
    assert "<material>" in request["messages"][0]["content"]


def test_refusal_becomes_an_explicit_failure():
    client = build_fake_client(build_response("", stop_reason="refusal"))

    result = LlmPriceExtractor(client=client, model="m").extract(NOTICE)

    assert not result.succeeded
    assert result.failure_code == "extraction.llm_failed"
    assert result.failure_params == {"reason": "refusal"}


def test_api_errors_become_explicit_failures():
    request = httpx2.Request("POST", "http://localhost:1/v1/messages")
    error = anthropic.APIConnectionError(request=request)
    client = build_fake_client(error=error)

    result = LlmPriceExtractor(client=client, model="m").extract(NOTICE)

    assert result.failure_params == {"reason": "connection_error"}


def test_empty_document_is_not_sent():
    client = build_fake_client()

    result = LlmPriceExtractor(client=client, model="m").extract(
        DocumentContent(text=" ", tables=())
    )

    assert result.failure_params == {"reason": "no_text"}
    assert client.beta.messages.requests == []


def test_pipeline_uses_fallback_only_when_no_table_is_found():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    client = build_fake_client(build_response(json.dumps(payload)))

    result = extract_prices(NOTICE, LlmPriceExtractor(client=client, model="m"))

    assert result.method == "llm"


def test_pipeline_without_fallback_reports_unrecognized_layout():
    result = extract_prices(NOTICE, None)

    assert result.failure_code == "extraction.layout_not_recognized"


def test_extractor_is_disabled_without_api_key():
    assert build_llm_extractor() is None
