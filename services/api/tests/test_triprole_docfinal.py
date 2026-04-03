from __future__ import annotations

import base64
import hashlib

from services.api.domain.execution.docfinal.triprole_docfinal import (
    apply_hierarchy_asset_filter,
    build_recursive_hierarchy_summary,
    encrypt_aes256,
    merkle_root_from_hashes,
    normalize_aggregate_direction,
    normalize_aggregate_level,
)


def test_merkle_root_from_hashes_uses_pairwise_merkle_logic() -> None:
    h1 = hashlib.sha256("a|b".encode("utf-8")).hexdigest()
    h2 = hashlib.sha256("c|c".encode("utf-8")).hexdigest()
    expected = hashlib.sha256(f"{h1}|{h2}".encode("utf-8")).hexdigest()
    assert merkle_root_from_hashes(["a", "b", "c"]) == expected


def test_normalize_aggregate_aliases() -> None:
    assert normalize_aggregate_direction("ancestor") == "up"
    assert normalize_aggregate_direction("lineage") == "both"
    assert normalize_aggregate_level("leaf") == "leaf"
    assert normalize_aggregate_level("unknown") == "all"


def test_build_recursive_hierarchy_summary_aggregates_tree_nodes() -> None:
    summary = build_recursive_hierarchy_summary(
        items=[
            {"item_no": "1-1-1", "design_quantity": 10, "settled_quantity": 4, "item_name": "A", "unit": "m"},
            {"item_no": "1-1-2", "design_quantity": 8, "settled_quantity": 2, "item_name": "B", "unit": "m"},
        ],
        focus_item_no="1-1-2",
    )

    assert summary["root_codes"] == ["1"]
    assert summary["chapter_progress"]["chapter_code"] == "1"
    assert len(summary["rows"]) == 4
    chapter_row = next(row for row in summary["rows"] if row["code"] == "1")
    assert chapter_row["design_quantity"] == 18.0
    assert chapter_row["settled_quantity"] == 6.0


def test_apply_hierarchy_asset_filter_direction_and_level() -> None:
    summary = build_recursive_hierarchy_summary(
        items=[
            {"item_no": "1-1-1", "design_quantity": 10, "settled_quantity": 4},
            {"item_no": "1-1-2", "design_quantity": 8, "settled_quantity": 2},
        ]
    )
    filtered = apply_hierarchy_asset_filter(
        rows=summary["rows"],
        focus_item_no="",
        anchor_code="1-1",
        direction="down",
        level="leaf",
    )

    assert filtered["filter"]["direction"] == "down"
    assert filtered["filter"]["level"] == "leaf"
    assert filtered["filter"]["filtered_row_count"] == 2
    assert {row["code"] for row in filtered["rows"]} == {"1-1-1", "1-1-2"}


def test_encrypt_aes256_returns_expected_shape() -> None:
    encrypted = encrypt_aes256(b"hello world", "passphrase")
    assert encrypted["algorithm"] == "AES-256-GCM"
    assert encrypted["aad"] == "QCSpec-Master-DSP-v1"
    assert len(base64.b64decode(encrypted["nonce_b64"])) == 12
    assert len(encrypted["cipher_hash"]) == 64
    assert encrypted["ciphertext_b64"]
