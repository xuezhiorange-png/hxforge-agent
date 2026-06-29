# TASK-010 — Versioned API and Traceable Report Contract

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** PENDING
**Frozen Contract SHA:** NOT ESTABLISHED
**Implementation Authorization:** NOT GRANTED

---

## 1. Scope

Freeze the normative API surface, response envelope, idempotency semantics, and HTML report contract for the hxforge-agent double-pipe vertical slice. Non-goals: production API implementation, HTML template engine, PDF engine, database, authentication/authorization, C4, pressure drop, velocity constraints, materials, cost, procurement readiness, TASK-011+.

---

## 2. Upstream Dependencies

| Artifact | Status | Reference |
|---|---|---|
| TASK-008 `RatingResult` | Production (frozen) | `src/hexagent/exchangers/double_pipe/result.py` |
| TASK-009 `OptimizationResult` | Production (frozen) | `src/hexagent/optimization/phase3_builder.py` |
| TASK-009 `Phase3EvaluationInput` | Production (frozen) | `src/hexagent/optimization/phase3_evaluation.py` |
| `DoublePipeService` class | NOT frozen — placeholder only | Out of scope for this contract |
| `assumed_u_w_m2_k = 500` | NOT frozen — placeholder only | Out of scope for this contract |

---

## 3. API Endpoints

### 3.1 Endpoint Summary

| Method | Path | operation_id | Description |
|---|---|---|---|
| POST | `/v1/cases/validate` | `validateCase` | Validate a sizing request without executing sizing |
| POST | `/v1/double-pipe/rating` | `rateDoublePipe` | Execute fixed-geometry double-pipe rating |
| POST | `/v1/double-pipe/sizing` | `sizeDoublePipe` | Execute manufacturable sizing + Top-N optimization |
| GET | `/v1/runs/{run_id}` | `getRun` | Retrieve a completed run's result envelope |
| GET | `/v1/runs/{run_id}/report.html` | `getRunReportHtml` | Retrieve the traceable HTML report |
| GET | `/v1/runs/{run_id}/report.pdf` | `getRunReportPdf` | Retrieve the traceable PDF report |

### 3.2 `POST /v1/cases/validate`

- **operation_id:** `validateCase`
- **Request:** `SizingRequest` (canonical JSON, `extra="forbid"`)
- **Response:** `RunEnvelope` with `result_kind = "validation"` and no domain computation result
- **Status mapping:** `200` on success; `422` on schema/unit/enum/cross-field failure
- **Idempotency:** Not enforced (validation-only endpoint)
- **Result hash behavior:** Computed from canonical request payload only

### 3.3 `POST /v1/double-pipe/rating`

- **operation_id:** `rateDoublePipe`
- **Request:** `RatingRequest` (geometry + fluids + boundary conditions + provider)
- **Response:** `RunEnvelope` with `result_kind = "rating"`, `result = RatingResult`
- **Domain status → HTTP:** `SUCCEEDED` → `200`; `BLOCKED` → `200`; controlled `FAILED` → `200`
- **HTTP 500:** Only for unexpected server exceptions (never for domain BLOCKED/FAILED)
- **Idempotency:** Required (`Idempotency-Key` header)
- **Result hash:** From `RatingResult` provenance chain (TASK-008 frozen)

### 3.4 `POST /v1/double-pipe/sizing`

- **operation_id:** `sizeDoublePipe`
- **Request:** `SizingRequest` (target duty + constraints + catalog + materialization parameters)
- **Response:** `RunEnvelope` with `result_kind = "sizing"`, `result = OptimizationResult`
- **Domain status → HTTP:** `COMPLETE` → `200`; `PARTIAL` (strict-stop) → `200`; input rejection → `422`
- **HTTP 500:** Only for unexpected exceptions
- **Forbidden:** `DoublePipeService.size()` and any placeholder sizing logic (assumed U, hardcoded area, starter result)
- **Idempotency:** Required
- **Result hash:** From `OptimizationResult.result_hash` (TASK-009 frozen)

### 3.5 `GET /v1/runs/{run_id}`

- **operation_id:** `getRun`
- **Path param:** `run_id: str` (UUID, validated as non-empty)
- **Response:** `RunEnvelope` (the stored envelope from the original POST)
- **Status mapping:** `200` if run exists; `404` if run_id unknown
- **Idempotency:** Read-only — not enforced

### 3.6 `GET /v1/runs/{run_id}/report.html`

- **operation_id:** `getRunReportHtml`
- **Response:** `text/html; charset=utf-8` — the traceable HTML report
- **Status mapping:** `200` (report exists); `404` (run unknown); `500` (unexpected rendering failure)
- **Report authority:** Built exclusively from the stored `RunEnvelope` — no re-computation, no template-side engineering logic

### 3.7 `GET /v1/runs/{run_id}/report.pdf`

- **operation_id:** `getRunReportPdf`
- **Response:** `application/pdf` when a `PdfReportAdapter` is configured
- **Status mapping:** `200` (PDF rendered); `404` (run unknown); `501` (no adapter configured)
- **No adapter:** Returns structured error via JSON error envelope (not an empty PDF, not a fake link)
- **Boundary:** PDF engine selection and integration is out of scope for this contract

---

## 4. HTTP ↔ Domain Status Mapping

| HTTP Status | Domain Condition | Notes |
|---|---|---|
| `200` | Request executed; domain result can be SUCCEEDED, BLOCKED, or controlled FAILED | BLOCKED/FAILED are engineering outcomes, not server errors |
| `404` | `run_id` not found in repository | Run never existed or was evicted |
| `409` | Same `Idempotency-Key` with different canonical request payload | Clearly distinguishable from 422 |
| `422` | Schema/unit/enum/cross-field validation failure | Pydantic validation error detail |
| `500` | Unexpected server exception | No traceback, absolute paths, or internal repr leaked |
| `501` | PDF endpoint reached but no `PdfReportAdapter` configured | Structured error body |

---

## 5. Idempotency Contract

### 5.1 Request Header

```
Idempotency-Key: <1-128 printable ASCII, trimmed, no control characters>
```

### 5.2 Identity Binding

The idempotency identity is a sha256 digest of:

```python
{
    "api_schema_version": "1",
    "operation_id": "<the endpoint operation_id>",
    "canonical_request_payload_digest": "<sha256 of canonical JSON with sorted keys>",
    "idempotency_key_digest": sha256_digest(idempotency_key_trimmed),
}
```

### 5.3 Behavior

| Condition | Outcome |
|---|---|
| Same key + same operation + same canonical payload | Return same `run_id` and same `RunEnvelope` |
| Same key + same operation + different canonical payload | `HTTP 409` — key collision |
| Same key + different operation | Independent idempotency namespaces (the identity binding includes `operation_id`) |
| JSON key order change in request | No effect (canonical JSON normalises key order) |

### 5.4 Run Repository (v0.1)

```python
from typing import Protocol

class RunRepository(Protocol):
    """Process-local, non-persistent run store."""

    def get(self, run_id: str) -> RunEnvelope | None: ...
    def put(self, run_id: str, envelope: RunEnvelope) -> None: ...


class InMemoryRunRepository:
    """Reference implementation — lost on restart, no multi-process consistency."""

    def __init__(self) -> None:
        self._store: dict[str, RunEnvelope] = {}

    def get(self, run_id: str) -> RunEnvelope | None:
        return self._store.get(run_id)

    def put(self, run_id: str, envelope: RunEnvelope) -> None:
        self._store[run_id] = envelope
```

- Process-local only
- No persistence
- Lost on restart
- No multi-process consistency
- Does not claim exactly-once delivery

This task does **not** introduce a database.

---

## 6. Unified Response Envelope

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal

class RunEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    api_schema_version: Literal["1"]
    operation: str                       # operation_id
    run_id: str
    idempotency_key_digest: str | None   # None when idempotency not enforced
    request_digest: str                  # sha256 of canonical request
    result_kind: Literal["validation", "rating", "sizing"]
    result: RatingResult | OptimizationResult | None  # domain-type discriminated
    result_hash: str                     # provenance-derived hash
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None           # structural failure (classifier-side)
    provenance: ProvenanceGraph | None   # TASK-008/TASK-009 provenance graph
    report_links: ReportLinks
```

### 6.1 Constraints

- `extra="forbid"` — unknown fields rejected
- `schema_version` is an explicit frozen literal
- `result` uses typed domain models, never `dict[str, Any]`
- `result_hash` is always present (deterministic from domain result)
- Run metadata excluded from `result_hash`: timestamp, process ID, host name, trace ID, temporary path, random `run_id`

### 6.2 `ReportLinks`

```python
class ReportLinks(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    html: str | None   # relative URI, e.g. "/v1/runs/{run_id}/report.html"
    pdf: str | None    # relative URI, or None if PDF adapter not configured
```

---

## 7. Report Authority Contract

### 7.1 Immutable Report Model

```python
class DoublePipeReportModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    report_schema_version: Literal["1"]
    run_envelope_digest: str            # sha256 of source RunEnvelope
    sections: tuple[ReportSection, ...]
    report_model_hash: str              # sha256 of canonical sections payload


class ReportSection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    section_id: str                     # e.g. "heat_balance", "geometry"
    status: ReportSectionStatus
    artifacts: tuple[ReportArtifact, ...]


class ReportSectionStatus(StrEnum):
    PRESENT = "present"
    NOT_AVAILABLE = "not_available"
    NOT_IMPLEMENTED = "not_implemented"
    OUT_OF_SCOPE = "out_of_scope"


class ReportArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    label: str                          # human-readable label
    value: ReportValueBinding | None    # None when status != PRESENT
    unit: str | None
    source_json_pointer: str            # path into source envelope
    status: ReportSectionStatus
```

### 7.2 `ReportValueBinding`

```python
class ReportValueBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    canonical_displayed_value: str      # formatted for display
    source_result_hash: str             # hash of the source result this value came from
    source_json_pointer: str            # exact pointer into source envelope
    unit: str | None
```

### 7.3 Authority Rules

- Every engineering display value MUST have a `ReportValueBinding` with exact `source_json_pointer` and `source_result_hash`
- The HTML report MUST check: stored `report_model_hash` matches recomputed hash from sections
- Mismatch → report rendering fails closed (no partial report, no best-effort output)
- Template MUST NOT:
  - Re-compute heat balance, rating, sizing, or ranking
  - Re-order or re-score candidates
  - Correct or fill in missing values
  - Invent values (even plausible ones)

---

## 8. Report Sections

### 8.1 Required Sections

| section_id | Source | Status when unavailable |
|---|---|---|
| `status_banner` | `result_kind`, `blockers`, `failure` | Always PRESENT |
| `run_identity` | `run_id`, `request_digest`, `result_hash` | Always PRESENT |
| `input_summary` | Canonical request | PRESENT or NOT_AVAILABLE |
| `heat_balance` | `RatingResult.heat_balance` | PRESENT or NOT_AVAILABLE |
| `geometry` | `RatingResult.geometry_snapshot` | PRESENT or NOT_AVAILABLE |
| `thermal_performance` | `RatingResult` (heat duty, LMTD, UA, terminal temps) | PRESENT or NOT_AVAILABLE |
| `sizing_ranking` | `OptimizationResult.ranked_records` | PRESENT or NOT_AVAILABLE |
| `selected_candidate` | `OptimizationResult` Top-N selection | PRESENT or NOT_AVAILABLE |
| `warnings` | `RunEnvelope.warnings` | PRESENT or NOT_AVAILABLE |
| `blockers` | `RunEnvelope.blockers` | PRESENT or NOT_AVAILABLE |
| `failure_details` | `RunEnvelope.failure` | PRESENT or NOT_AVAILABLE |
| `provenance` | `RunEnvelope.provenance` | PRESENT or NOT_AVAILABLE |
| `integrity` | `report_model_hash`, `result_hash`, `request_digest` | Always PRESENT |

### 8.2 Not-Implemented Capabilities

The following MUST display `NOT_IMPLEMENTED` or `OUT_OF_SCOPE` (never `0`, `PASS`, `COMPLIANT`, or `ACCEPTABLE`):

| Capability | Status |
|---|---|
| Pressure drop | NOT_IMPLEMENTED |
| Velocity constraints | NOT_IMPLEMENTED |
| Materials | OUT_OF_SCOPE |
| Cost | OUT_OF_SCOPE |
| Mechanical compliance | OUT_OF_SCOPE |
| Procurement readiness | OUT_OF_SCOPE |

---

## 9. Status and Risk Display

### 9.1 Every Print Page

Every HTML page produced by the report renderer MUST display the following prominently:

```
PRELIMINARY
NOT FOR PROCUREMENT
NOT FOR CONSTRUCTION
```

This is a static boilerplate inserted by the renderer — not a template variable the user can suppress.

### 9.2 Blocker Display

- When `RunEnvelope.blockers` is non-empty, blockers MUST appear at the **top** of the report (above the status banner or integrated into it)
- Blockers MUST NOT be restricted to an appendix
- Blockers MUST NOT be softened by narrative text
- Blockers MUST NOT rely exclusively on color to convey severity (use text + icon + position)

---

## 10. HTML Security Contract

- Template engine autoescape MUST be enabled (HTML-escape all variables by default)
- User-specified template path is forbidden
- Arbitrary file-system reads are forbidden
- External network resources (CDNs, fonts, tracking pixels) are forbidden
- User-provided input (case name, fluid name, message content, context tuples) MUST be HTML-escaped
- Environment variables, tokens, absolute paths, and tracebacks MUST NOT appear in rendered output
- No use of `| safe` or equivalent on user-originated data

---

## 11. PDF Boundary

```python
from typing import Protocol

class PdfReportAdapter(Protocol):
    """Minimal protocol for PDF rendering — engine selection is out of scope."""

    def render_pdf(self, html: str, *, report_id: str) -> bytes:
        """Return PDF bytes given validated HTML content."""
        ...
```

- When no `PdfReportAdapter` is configured:
  - `GET /v1/runs/{run_id}/report.html` works normally
  - `GET /v1/runs/{run_id}/report.pdf` returns `HTTP 501` with a structured JSON error body
  - No empty PDF, no fake PDF link, no degraded HTML-to-PDF fallback
- Selection and integration of a specific PDF engine (WeasyPrint, wkhtmltopdf, etc.) is **out of scope** for this contract

---

## 12. Determinism Contract

Given identical inputs:

| Input | Deterministic Output |
|---|---|
| Canonical request payload | `request_digest` |
| Provider identity (name + version + config fingerprint) | Same domain result |
| Catalog identity (frozen catalog SHA) | Same `OptimizationResult` |
| Solver settings (tolerances, max iterations) | Same solver convergence |
| Template version | Same HTML structure |
| Report model version | Same `report_model_hash` |

**Excluded from engineering hashes** (run-level metadata):

| Field | Rationale |
|---|---|
| `current_time` / timestamp | Non-deterministic |
| `run_id` | Random UUID |
| Process ID | OS-specific |
| Host name | Environment-specific |
| Trace ID | Observability, not engineering |
| Temporary directory | File-system layout |

The `report_model_hash` is computed from `tuple[ReportSection, ...]` canonical payload — same sections with same artifact bindings MUST produce the same hash.

---

## 13. Error Envelope

```python
class ApiError(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    api_schema_version: Literal["1"]
    operation: str | None
    status_code: int
    error_code: str                     # internal machine-readable code
    error_message: str                  # human-readable, no traceback
    request_digest: str | None
    details: tuple[ErrorDetail, ...]    # structured context, no absolute paths


class ErrorDetail(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    field: str | None                   # JSON pointer or empty
    reason: str
    value: str | None                   # truncated, redacted
```

---

## 14. Test Contract

The following tests MUST be defined in the implementation phase (this contract freezes the list, not the test bodies):

| # | Test | Expected Outcome |
|---|---|---|
| T1 | OpenAPI `operation_id` values are unique and stable | 6 unique IDs |
| T2 | Request/response JSON Schema exportable | Valid JSON Schema draft-07 |
| T3 | Unknown field in request → `422` | Pydantic `extra="forbid"` |
| T4 | Invalid unit string → `422` | Enum validation failure |
| T5 | Same key + same payload → same `run_id` | 2 calls return identical envelope |
| T6 | Same key + JSON key order changed → still hits | Canonical JSON normalisation |
| T7 | Same key + different payload → `409` | Idempotency collision |
| T8 | Same key + different `operation_id` → independent | Separate idempotency namespaces |
| T9 | `BLOCKED` rating result → `HTTP 200` | Not `500` |
| T10 | Unknown `run_id` → `404` | Repository miss |
| T11 | Unhandled exception → `HTTP 500` with no traceback or path leak | Regex on response body |
| T12 | Placeholder sizing service unreachable / not imported | Test proves old code absent |
| T13 | Report `ReportValueBinding` matches envelope value at `source_json_pointer` | Exact match per artifact |
| T14 | Tampered `result_hash` in envelope → report render rejects | Fail-closed |
| T15 | Blocker present → appears in top banner of HTML | String search in rendered HTML |
| T16 | Every print page contains "PRELIMINARY" / "NOT FOR PROCUREMENT" / "NOT FOR CONSTRUCTION" | 3-string presence check |
| T17 | HTML injection string (`<script>alert(1)</script>`) in case name → escaped | `&lt;script&gt;` in output |
| T18 | Pressure drop, materials, cost display `NOT_IMPLEMENTED` / `OUT_OF_SCOPE` | String search |
| T19 | PDF endpoint with no adapter → `HTTP 501` | Structured error body |
| T20 | Same canonical request → same HTML engineering content (byte-level) | `report_model_hash` equality |
| T21 | Python 3.11 full suite passes | Exit 0 |
| T22 | Python 3.12 full suite passes | Exit 0 |

---

## 15. Explicit Exclusions

The following are **not** in scope for TASK-010 design or implementation:

- Production API server (routing, middleware, WSGI/ASGI)
- HTML template engine or HTML rendering implementation
- PDF engine selection, integration, or rendering
- Database, ORM, or persistent storage
- Object storage for report artifacts
- Authentication, authorization, or rate limiting
- TASK-011+ (multi-exchanger, C4, advanced optimization)
- C4, pressure drop, velocity constraints, materials, cost, mechanical compliance
- Stochastic or heuristic optimization
- Procurement conclusions or compliance claims

---

## 16. Design Status

| Field | Value |
|---|---|
| TASK-010 design | READY_FOR_REVIEW |
| TASK-010 implementation | BLOCKED |
| Frozen Contract SHA | NOT ESTABLISHED |
| Implementation Authorization | NOT GRANTED |
