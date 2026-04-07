from __future__ import annotations

from services.api.domain.boqpeg import parse_boq_upload as boqpeg_parse_boq_upload
from services.api.domain.smu.runtime.smu_boq_upload_parser import parse_boq_upload


def test_smu_boq_upload_parser_points_to_boqpeg() -> None:
    assert parse_boq_upload is boqpeg_parse_boq_upload

