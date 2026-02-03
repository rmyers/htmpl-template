# cuneus/ext/observability/store.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass
class TraceRecord:
    trace_id: str
    root_span_name: str
    service: str
    started_at: datetime
    duration_ms: int
    status: str  # OK, ERROR


@dataclass
class SpanRecord:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    kind: str
    started_at: datetime
    duration_ms: int
    status: str
    attributes: dict | None = None
    events: list | None = None


@dataclass
class ExceptionRecord:
    id: int
    ts: datetime
    trace_id: str | None
    span_id: str | None
    fingerprint: str
    exc_type: str
    message: str
    tb: str
    ctx: dict | None = None


@dataclass
class DashboardStats:
    trace_count: int
    error_count: int
    error_rate: float
    avg_duration_ms: float
    recent_traces: list[TraceRecord]
    recent_exceptions: list[ExceptionRecord]


@runtime_checkable
class Store(Protocol):
    """Protocol for observability storage."""

    def insert_trace(self, trace: TraceRecord) -> None: ...
    def insert_span(self, span: SpanRecord) -> None: ...
    def insert_exception(self, exc: ExceptionRecord) -> None: ...

    def get_traces(
        self, page: int = 1, per_page: int = 50, status: str | None = None
    ) -> tuple[list[TraceRecord], int]: ...
    def get_trace(self, trace_id: str) -> TraceRecord | None: ...
    def get_spans_for_trace(self, trace_id: str) -> list[SpanRecord]: ...

    def get_exceptions(
        self, page: int = 1, per_page: int = 50
    ) -> tuple[list[ExceptionRecord], int]: ...
    def get_exception(self, exc_id: int) -> ExceptionRecord | None: ...

    def get_dashboard_stats(self) -> DashboardStats: ...


@dataclass
class InMemoryStore:
    """Simple in-memory store for development/testing."""

    traces: dict[str, TraceRecord] = field(default_factory=dict)
    spans: list[SpanRecord] = field(default_factory=list)
    exceptions: list[ExceptionRecord] = field(default_factory=list)
    _exc_id_counter: int = 0

    def insert_trace(self, trace: TraceRecord) -> None:
        self.traces[trace.trace_id] = trace

    def insert_span(self, span: SpanRecord) -> None:
        self.spans.append(span)

    def insert_exception(self, exc: ExceptionRecord) -> None:
        self._exc_id_counter += 1
        exc.id = self._exc_id_counter
        self.exceptions.append(exc)

    def get_traces(
        self, page: int = 1, per_page: int = 50, status: str | None = None
    ) -> tuple[list[TraceRecord], int]:
        traces = list(self.traces.values())
        if status:
            traces = [t for t in traces if t.status == status]
        traces.sort(key=lambda t: t.started_at, reverse=True)

        total = len(traces)
        start = (page - 1) * per_page
        end = start + per_page

        return traces[start:end], total

    def get_trace(self, trace_id: str) -> TraceRecord | None:
        return self.traces.get(trace_id)

    def get_spans_for_trace(self, trace_id: str) -> list[SpanRecord]:
        spans = [s for s in self.spans if s.trace_id == trace_id]
        spans.sort(key=lambda s: s.started_at)
        return spans

    def get_exceptions(
        self, page: int = 1, per_page: int = 50
    ) -> tuple[list[ExceptionRecord], int]:
        exceptions = sorted(self.exceptions, key=lambda e: e.ts, reverse=True)
        total = len(exceptions)
        start = (page - 1) * per_page
        end = start + per_page
        return exceptions[start:end], total

    def get_exception(self, exc_id: int) -> ExceptionRecord | None:
        for exc in self.exceptions:
            if exc.id == exc_id:
                return exc
        return None

    def get_dashboard_stats(self) -> DashboardStats:
        traces = list(self.traces.values())
        trace_count = len(traces)
        error_count = sum(1 for t in traces if t.status == "ERROR")
        error_rate = (error_count / trace_count * 100) if trace_count else 0
        avg_duration = (
            sum(t.duration_ms for t in traces) / trace_count if trace_count else 0
        )

        recent_traces = sorted(traces, key=lambda t: t.started_at, reverse=True)[:10]
        recent_exceptions = sorted(self.exceptions, key=lambda e: e.ts, reverse=True)[
            :10
        ]

        return DashboardStats(
            trace_count=trace_count,
            error_count=error_count,
            error_rate=error_rate,
            avg_duration_ms=avg_duration,
            recent_traces=recent_traces,
            recent_exceptions=recent_exceptions,
        )
