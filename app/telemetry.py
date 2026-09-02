"""Observability wiring.  Spec: IMPLEMENTATION_PLAN.md §8.9.

Phase: IMPLEMENTED IN P4.  Strands is OTEL-native; on AgentCore enable CloudWatch
Transaction Search and instrument with ADOT (opentelemetry-instrument). Set log
retention + X-Ray sampling low to control cost (§12).
"""
from __future__ import annotations


def setup_local_console():
    """Print spans to console for local debugging. Optional in P2/P3."""
    from strands.telemetry import StrandsTelemetry
    t = StrandsTelemetry()
    t.setup_console_exporter()
    return t


def setup_otlp():
    """Export via OTLP (for CloudWatch/Langfuse/etc.). P4."""
    from strands.telemetry import StrandsTelemetry
    t = StrandsTelemetry()
    t.setup_otlp_exporter()
    return t
