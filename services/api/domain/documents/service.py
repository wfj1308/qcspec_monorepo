"""Document governance facade."""

from __future__ import annotations

from typing import Any

from supabase import Client

from services.api.core.base import BaseService
from services.api.proof_flow_service import (
    doc_auto_classify_flow,
    doc_auto_generate_nodes_flow,
    doc_create_node_flow,
    doc_register_upload_flow,
    doc_search_flow,
    doc_tree_flow,
)


class DocumentGovernanceService(BaseService):
    def __init__(self, *, sb: Client) -> None:
        super().__init__(sb=sb)

    async def auto_classify(self, *, body: Any) -> Any:
        return await self.run_guarded("doc_auto_classify", doc_auto_classify_flow, body=body)

    async def tree(self, *, project_uri: str, root_uri: str = "") -> Any:
        return await self.run_guarded("doc_tree", doc_tree_flow, project_uri=project_uri, root_uri=root_uri, sb=self.require_supabase())

    async def create_node(self, *, body: Any) -> Any:
        return await self.run_guarded("doc_create_node", doc_create_node_flow, body=body, sb=self.require_supabase())

    async def auto_generate_nodes(self, *, body: Any) -> Any:
        return await self.run_guarded("doc_auto_generate_nodes", doc_auto_generate_nodes_flow, body=body, sb=self.require_supabase())

    async def search(self, *, body: Any) -> Any:
        return await self.run_guarded("doc_search", doc_search_flow, body=body, sb=self.require_supabase())

    async def register_upload(self, **kwargs: Any) -> Any:
        return await self.run_guarded("doc_register_upload", doc_register_upload_flow, sb=self.require_supabase(), **kwargs)
