"""AgentCore Runtime entrypoint.  Spec: IMPLEMENTATION_PLAN.md §8.1.

Phase: implemented in P4 (deploy). In P2/P3 the graph is driven directly by
scripts/run_local_demo.py without the AgentCore wrapper.

Run locally:
    python app/main.py
    curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" \
      -d '{"mode":"event","org_id":"demo-pantry","payload":{"sms":"40 lbs of milk to donate"}}'
"""
from __future__ import annotations

# NOTE: import guarded so the module is importable before bedrock-agentcore is installed.
try:
    from bedrock_agentcore.runtime import BedrockAgentCoreApp
except Exception:  # pragma: no cover
    BedrockAgentCoreApp = None  # type: ignore


def _build():
    from app.graph import build_steward_graph
    return build_steward_graph()


def _make_app():
    if BedrockAgentCoreApp is None:
        raise RuntimeError("bedrock-agentcore not installed; run `pip install -r requirements.txt`")
    app = BedrockAgentCoreApp()
    graph = _build()

    @app.entrypoint
    def invoke(payload):  # noqa: ANN001
        mode = payload.get("mode", "event")          # "sweep" | "event"
        org_id = payload["org_id"]
        task_input = payload.get("payload", {})
        result = graph({"mode": mode, "org_id": org_id, "input": task_input})
        # Escalation: a Strands interrupt bubbles up as stop_reason == "interrupt" (§8.5).
        if getattr(result, "stop_reason", None) == "interrupt":
            return {"status": "escalated", "interrupts": [i.name for i in result.interrupts]}
        return {"status": "ok", "result": str(getattr(result, "message", result))}

    return app


if __name__ == "__main__":  # pragma: no cover
    _make_app().run()   # serves POST /invocations, GET /ping on :8080
