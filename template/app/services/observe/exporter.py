# cuneus/ext/observability/exporter.py
from __future__ import annotations

from datetime import datetime, timezone

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import StatusCode

from .store import Store, TraceRecord, SpanRecord


class StoreSpanExporter(SpanExporter):
    """Exports spans to an observability store."""

    def __init__(self, store: Store):
        self.store = store

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            assert span.context
            assert span.start_time
            assert span.end_time

            trace_id = format(span.context.trace_id, "032x")
            span_id = format(span.context.span_id, "016x")
            parent_id = format(span.parent.span_id, "016x") if span.parent else None

            started = datetime.fromtimestamp(span.start_time / 1e9, tz=timezone.utc)
            duration = (span.end_time - span.start_time) // 1_000_000
            status = "ERROR" if span.status.status_code == StatusCode.ERROR else "OK"

            # Insert span
            self.store.insert_span(
                SpanRecord(
                    trace_id=trace_id,
                    span_id=span_id,
                    parent_span_id=parent_id,
                    name=span.name,
                    kind=span.kind.name if span.kind else "INTERNAL",
                    started_at=started,
                    duration_ms=duration,
                    status=status,
                    attributes=dict(span.attributes) if span.attributes else None,
                    events=_serialize_events(span.events),
                )
            )

            # Insert/update trace for root spans
            if parent_id is None:
                self.store.insert_trace(
                    TraceRecord(
                        trace_id=trace_id,
                        root_span_name=span.name,
                        service=_get_service(span),
                        started_at=started,
                        duration_ms=duration,
                        status=status,
                    )
                )

        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


def _get_service(span: ReadableSpan) -> str:
    if span.resource:
        return str(span.resource.attributes.get("service.name", "unknown"))
    return "unknown"


def _serialize_events(events) -> list | None:
    if not events:
        return None
    return [
        {
            "name": e.name,
            "timestamp": e.timestamp,
            "attributes": dict(e.attributes) if e.attributes else {},
        }
        for e in events
    ]
