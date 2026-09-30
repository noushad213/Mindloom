import json

import pytest
from pydantic import ValidationError

from app.schemas.pages import IngestPayload
from app.services.ingest import prepare_content


@pytest.mark.parametrize("field", ["url", "title"])
def test_required_fields(ingest_payload, field):
    del ingest_payload[field]
    with pytest.raises(ValidationError):
        IngestPayload.model_validate_json(json.dumps(ingest_payload))


def test_long_text_is_truncated(ingest_payload):
    ingest_payload["text"] = "a" * 100_010
    payload = IngestPayload.model_validate_json(json.dumps(ingest_payload))
    content, status, error, _ = prepare_content(payload, 100_000)
    assert len(content) == 100_000
    assert status == "extracted" and error is None


def test_json_strings_validate_as_uuid_and_timestamp(ingest_payload):
    payload = IngestPayload.model_validate(ingest_payload)
    assert str(payload.client_event_id) == ingest_payload["client_event_id"]
    assert payload.captured_at.utcoffset().total_seconds() == 0


def test_bad_extraction_status_rejected(ingest_payload):
    ingest_payload["extraction"]["status"] = "unknown"
    with pytest.raises(ValidationError):
        IngestPayload.model_validate_json(json.dumps(ingest_payload))


def test_failed_extraction_requires_reason(ingest_payload):
    ingest_payload["extraction"]["status"] = "failed"
    with pytest.raises(ValidationError):
        IngestPayload.model_validate_json(json.dumps(ingest_payload))


def test_empty_content_and_failed_extraction(ingest_payload):
    ingest_payload["text"] = "  "
    payload = IngestPayload.model_validate_json(json.dumps(ingest_payload))
    assert prepare_content(payload, 100_000)[1:3] == ("extraction_failed", "empty_content")
    ingest_payload["extraction"] = {"status": "failed", "method": "readability", "error_code": "no_permission", "error_message": "Denied"}
    payload = IngestPayload.model_validate_json(json.dumps(ingest_payload))
    assert prepare_content(payload, 100_000)[1:3] == ("extraction_failed", "no_permission")
