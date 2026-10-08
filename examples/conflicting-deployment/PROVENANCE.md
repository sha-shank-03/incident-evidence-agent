# Original fictional conflict fixture

Created 2026-10-07 for this repository; Apache-2.0. All services, logs, traces, IDs, versions, timings and deployment records are fictional original data. No company logs, real account data, credentials, vendor fixture code, or third-party dataset is used.

Three checkout failures occur at 10:02, 10:07 and 10:09 UTC. The checkout deployment is at 10:05. Three liveness probes explicitly record `probe_status=OK` on their own paths. One payment background error and one checkout error exactly at the excluded 10:20 boundary test service/time selectors. Nine spans describe the three checkout request paths. The span export is marked sampled.

The earlier failure is counter-evidence to the claim that this deployment initiated the entire incident. Later failures supply temporal association. Healthy probes do not disprove request failures. The narrow deployment hypothesis is mixed and the result remains inconclusive; no underlying cause is asserted. Separate expectations are in the parent `expectations.json`, outside the bundle and planner/tool inputs.
