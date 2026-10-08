# Synthetic fixture provenance

Created for this repository on 2026-10-07. All records, service names, requests, deployment events, versions, bodies, trace IDs, and timings are original fictional data. No real company logs, personal data, incident exports, credentials, third-party datasets, or copied vendor fixture files were used.

The fixture is original repository data licensed under Apache-2.0, like the source. Its normalized fields were informed by the OpenTelemetry specification v1.61.0 and W3C Trace Context Level 1 identifier rules; it is not an OTLP fixture or a conformance sample.

Contents: five fictional checkout request traces (three error paths and two successful paths), each with checkout root/client and payment server spans; three structured timeout error logs, five request-start logs, and a healthy liveness probe log. One checkout deployment predates the selected window. The export declares sampled spans and unknown change coverage so those limitations remain explicit.

Purpose: test record-level source linking, aggregate recomputation, trace/span correlation, adaptive mock tool choice, and a qualified failure-pattern hypothesis. It does not model a complete production incident or establish payment's underlying cause. Dedicated conflicting/inconclusive exercises are scheduled for M2 and are not part of this M1 fixture.
