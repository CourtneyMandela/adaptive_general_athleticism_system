# 0132 — Device-local prescribed-rest timer

Status: accepted

Date: 2026-09-22

## Decision

Add an athlete-controlled countdown after each non-final set in the live phone workout. The timer
starts only when the athlete taps **Start rest**, uses the exact `rest_seconds` from the immutable
prescription, and offers restart and cancel controls.

The countdown is device-local presentation state. It does not alter the prescription, start
automatically from a checkbox, survive as authoritative workout history, or claim that the athlete
actually rested for the displayed interval.

## Why

Showing “120s rest” while requiring a separate timer makes the live workout unnecessarily awkward.
The countdown makes the existing governed prescription usable without introducing a new training
rule or a false observation.

## Alternatives considered

- Persist timer events as performed rest. Rejected because a running browser countdown does not
  prove what the athlete did; actual-rest observation needs a separate explicit contract.
- Auto-start when a set is marked complete. Rejected because checking the box may happen after the
  set or during later review, and should not silently trigger behavior.
- Add sound, vibration, or notifications. Deferred until permission, accessibility, background-PWA,
  and user-preference behavior are designed.
