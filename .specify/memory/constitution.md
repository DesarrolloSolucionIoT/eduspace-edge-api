<!--
SYNC IMPACT REPORT
==================
Version change: (template, unratified) → 1.0.0
Rationale: Initial ratification of the project constitution. MAJOR bump from an
unfilled template to a concrete, governing v1.0.0.

Modified principles: none (initial adoption)
Added principles:
  - I. Layered Domain-Driven Architecture
  - II. Test-First Development (NON-NEGOTIABLE)
  - III. Disciplined Code Quality
  - IV. IoT Edge Resilience
  - V. Structured Error Handling
Added sections:
  - Additional Constraints (technology & operational)
  - Development Workflow & Quality Gates
Removed sections: none

Templates requiring updates:
  ✅ .specify/templates/plan-template.md  — Constitution Check gate references this file generically; no edit required.
  ✅ .specify/templates/spec-template.md  — No constitution-specific tokens; compatible as-is.
  ✅ .specify/templates/tasks-template.md — Test-first ordering already reflected; compatible as-is.

Follow-up TODOs: none
-->

# EduSpace Edge API Constitution

## Core Principles

### I. Layered Domain-Driven Architecture

The service MUST follow Domain-Driven Design with strict separation across four layers:
domain, application, infrastructure, and interfaces. Code MUST be organized by bounded
context, where each bounded context is an independent module owning its own layers.

Non-negotiable rules:

- The domain layer MUST NEVER import from infrastructure or interfaces.
- A bounded context MAY depend on another bounded context only through that context's
  application layer; reaching into another context's domain directly is forbidden.
- All external I/O — HTTP calls and database writes — MUST be isolated in the
  infrastructure layer. Domain and application code MUST NOT perform I/O directly.

**Rationale**: Strict layering keeps business rules pure and testable, prevents
infrastructure concerns from leaking into the domain, and allows bounded contexts to
evolve and be reasoned about independently.

### II. Test-First Development (NON-NEGOTIABLE)

All production code MUST be preceded by a failing unit test. The Red-Green-Refactor
cycle is mandatory: write the test, watch it fail, then implement.

Non-negotiable rules:

- Tests MUST cover happy paths, authentication failures, validation errors, and
  upstream forwarding failures for every behavior they protect.
- Integration tests MUST exercise the real SQLite database — mocking the database in
  integration tests is forbidden.
- No implementation is considered done without tests that explicitly validate the
  behavior described in the corresponding spec.

**Rationale**: Tests written first define the contract before the code exists, guard
against regression, and ensure the failure modes that matter most for an edge service
(auth, validation, upstream loss) are proven, not assumed.

### III. Disciplined Code Quality

Code MUST remain small, explicit, and dependency-injected.

Non-negotiable rules:

- Python type hints are mandatory on ALL function signatures.
- Modules MUST be small and single-purpose.
- No function may exceed 30 lines.
- Dependencies MUST be injected; business logic MUST NOT import its collaborators
  (clients, repositories, sessions) directly.

**Rationale**: Type hints and small, single-purpose units make code self-documenting
and statically checkable. Dependency injection keeps business logic decoupled from
concrete I/O, which is what makes Principles I and II achievable.

### IV. IoT Edge Resilience

The service MUST behave correctly and remain available under the realities of edge
deployment, where the upstream Web API and device clocks are unreliable.

Non-negotiable rules:

- Timestamps received from devices MUST be normalized to UTC before persistence.
- Device credentials MUST be validated on every request; the service MUST hold no
  session state (stateless authentication).
- The service MUST continue accepting and buffering sensor readings even when the
  upstream Web API is unreachable.
- The `alertLedState` returned to the device MUST be computed locally and MUST NOT
  depend on upstream availability.

**Rationale**: Edge devices depend on the local service being authoritative for
real-time control. Local computation of `alertLedState` and offline buffering ensure the
device keeps functioning during network partitions; UTC normalization and stateless auth
keep persisted data and access control correct regardless of device or connectivity state.

### V. Structured Error Handling

Every error surfaced by the service MUST be structured, predictable, and safe for the
device to consume.

Non-negotiable rules:

- Every error response MUST include a machine-readable code AND a human-readable message.
- HTTP status codes MUST be used consistently: 400 for validation errors, 401 for
  authentication failures, 503 for upstream unavailability.
- Upstream forwarding failures MUST be logged and queued for retry. They MUST NEVER
  produce a 5xx response back to the device (other than a deliberate 503 signalling
  upstream unavailability where the contract requires it).

**Rationale**: Devices need deterministic, parseable error semantics to react correctly.
Decoupling upstream forwarding from the device response (via logging + retry queues)
prevents upstream outages from cascading into device-facing failures.

## Additional Constraints

- **Language & typing**: Python with mandatory type hints; static type checking is part
  of the quality gate.
- **Persistence**: SQLite is the system of record at the edge. Integration tests run
  against a real SQLite instance.
- **Upstream integration**: Communication with the upstream Web API is asynchronous from
  the device's perspective — forwarding is mediated by a durable retry queue so device
  responses never block on upstream calls.
- **Statelessness**: No server-side session state may be introduced; any future caching
  must not become an implicit authentication or authorization store.

## Development Workflow & Quality Gates

- **Constitution Check**: Every implementation plan MUST pass a Constitution Check gate
  before research and again after design. Layer-boundary violations, missing tests, and
  functions exceeding 30 lines are gate failures.
- **Test gate**: A change MUST NOT merge unless its unit tests (covering happy path, auth
  failure, validation error, and upstream failure as applicable) and SQLite-backed
  integration tests pass.
- **Review**: Reviewers MUST verify layer separation, dependency injection, type-hint
  coverage, and error-response structure. Any deviation MUST be justified in the plan's
  Complexity Tracking section or rejected.
- **Documentation of complexity**: Any violation of a principle that is nonetheless
  accepted MUST be recorded with its justification and the simpler alternative that was
  rejected and why.

## Governance

This constitution supersedes all other development practices. When guidance conflicts,
the constitution prevails.

- **Amendments**: Changes to this constitution MUST be proposed in writing, reviewed,
  and approved. Each amendment MUST document its rationale and any migration impact on
  existing code and dependent templates.
- **Versioning policy**: This constitution is versioned with semantic versioning.
  MAJOR — backward-incompatible governance or principle removals/redefinitions;
  MINOR — a new principle or materially expanded guidance is added;
  PATCH — clarifications, wording, or non-semantic refinements.
- **Compliance review**: All pull requests and reviews MUST verify compliance with these
  principles. Complexity that violates a principle MUST be justified or removed. Use the
  Spec Kit plan, spec, and tasks templates under `.specify/templates/` for runtime
  development guidance aligned to this constitution.

**Version**: 1.0.0 | **Ratified**: 2026-05-30 | **Last Amended**: 2026-05-30
