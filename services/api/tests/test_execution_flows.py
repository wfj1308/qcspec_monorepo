from __future__ import annotations

from services.api.domain.execution import flows


class _FakeTriproleModule:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute_triprole_action(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("execute_triprole_action", kwargs))
        return {"ok": True, "kind": "execute"}

    def replay_offline_packets(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("replay_offline_packets", kwargs))
        return {"ok": True, "kind": "replay"}

    def export_doc_final(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(("export_doc_final", kwargs))
        return {"ok": True, "kind": "export"}


def test_execution_flows_delegate_triprole_actions(monkeypatch) -> None:
    fake = _FakeTriproleModule()
    monkeypatch.setattr(flows, "_triprole_engine_module", lambda: fake)

    execute_out = flows.execute_triprole_action(sb=object(), body={"action": "quality.check"})
    replay_out = flows.replay_offline_packets(sb=object(), packets=[], stop_on_error=False)
    export_out = flows.export_doc_final(sb=object(), project_uri="v://project/demo")

    assert execute_out == {"ok": True, "kind": "execute"}
    assert replay_out == {"ok": True, "kind": "replay"}
    assert export_out == {"ok": True, "kind": "export"}
    assert [name for name, _ in fake.calls] == [
        "execute_triprole_action",
        "replay_offline_packets",
        "export_doc_final",
    ]
