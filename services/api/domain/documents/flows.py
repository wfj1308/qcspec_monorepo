"""Canonical documents-domain flow entry points."""

from __future__ import annotations

from services.api.domain.documents.integrations import (
    auto_classify_document,
    auto_generate_stake_nodes,
    create_node,
    list_node_tree,
    register_document,
    search_documents,
)

__all__ = [
    "auto_classify_document",
    "create_node",
    "auto_generate_stake_nodes",
    "list_node_tree",
    "search_documents",
    "register_document",
]
