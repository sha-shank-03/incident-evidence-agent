# Fictional tool failure schedules

Original Apache-2.0 demonstration data, created 2026-10-07. Profiles simulate the first `traces_find` transient failure with recovery, two transient failures exhausting retry-once, or one permanent `changes_list` failure. They describe no real outage and perform no network calls or side effects.

The caller explicitly supplies a profile; it is not planner-controlled. Each injected failure consumes the same call budget as a normal attempt. Generated report/event labels retain that this is fictional injection. Profile consistency and source verification do not authenticate historical execution.
