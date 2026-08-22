# Decision 0020: Transactional completed-block review

- Status: accepted
- Date: 2026-08-22

## Context

The domain already represented immutable training responses and block reviews, and replanning could
consume a persisted review. The missing application boundary allowed tests or future callers to
assemble review inputs selectively. That would make it possible to omit missed weeks, executions,
adherence, or unfavorable safety history and would weaken the first closed feedback loop.

## Decision

Add one FastAPI application service at `POST /v1/blocks/{block_id}/reviews`. Keep calculation in the
existing deterministic `TrainingResponseCalculator` and `BlockReviewEngine`; the application layer
only reconstructs governed inputs and owns the transaction.

V1 requires exactly one feasible weekly plan for each dated week of the block. Every planned
session must have one persisted execution outcome, including an explicit `NOT_STARTED` outcome for
a missed session, and every execution item must have derived adherence. At least one post-session
safety decision must exist for every execution, and the service loads all of them.

Response drafts must form an exact, non-overlapping partition of all unique prescription IDs used
by those executions. A draft supplies its adaptation, baseline and follow-up estimate IDs,
uncertainty, contextual factors, comparison direction, and meaningful-change threshold. The
service neither invents nor infers those scientific or operational inputs. Baselines may not
postdate block start; follow-up estimates and review may not predate planned block end.

All newly derived `TrainingResponse` records and the `BlockReview` commit or roll back together. A
database uniqueness constraint permits one completed review per block in V1. Historical estimates,
observations, prescriptions, executions, and strategies are not updated.

## Alternatives considered

- Accept weekly-plan, execution, adherence, or safety IDs from the caller. Rejected because a caller
  could omit inconvenient history or cross an incorrect lineage boundary.
- Review any subset of completed weeks. Rejected because it would label an interim analysis as a
  completed-block review; an explicit interim-review concept can be added later if needed.
- Infer meaningful change from observed variance or a generic percentage. Rejected because the
  repository has no reviewed evidence or population-specific rule authorizing such a threshold.
- Update capability state in the same transaction. Rejected because response attribution and
  current-state estimation are distinct; replanning already consumes an independently derived
  follow-up estimate.
- Permit multiple reviews and select a current one. Deferred until correction/supersession semantics
  are explicit; competing reviews would make downstream strategy lineage ambiguous.

## Assumptions

- Block weeks are contiguous seven-day windows beginning at `BlockPlan.starts_on`.
- A feasible persisted weekly plan is the authoritative schedule for that week in V1.
- One response may aggregate repeated delivery of the same prescription across the block, while
  one response cannot mix repetition- and duration-based dose units.
- A block can be reviewed after its planned end even when its original allocation status was
  partial, provided the scheduled history is complete and the review retains that block hypothesis.

## Unresolved questions

- How a corrected weekly plan or completed review explicitly supersedes its predecessor.
- Whether future interim reviews need a separate record type and downstream permissions.
- Which reviewed evidence packages will authorize production review policies and metric-specific
  meaningful-change thresholds.
- Whether follow-up measurement timing needs metric-specific windows beyond the conservative block-
  end rule.

## Consequences

The persisted path now spans block schedule, execution, safety, adherence, training response,
completed review, and successor-strategy derivation without raw CRUD or caller-selected historical
subsets. The stricter completeness boundary requires clients to log missed sessions explicitly and
does not yet support review correction; both limitations are visible rather than silently guessed.
