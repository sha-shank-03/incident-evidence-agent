# Dependency and reference attribution

The final package has **no third-party runtime/test packages**. It uses an externally installed CPython 3.11.9 and its standard library; Python is not bundled or redistributed. CPython's license is PSF License Version 2 plus its incorporated-software notices: [tagged LICENSE](https://raw.githubusercontent.com/python/cpython/v3.11.9/LICENSE), re-read 2026-10-08.

Design references, read 2026-10-07 (no source code or third-party incident data copied):

- OpenTelemetry specification v1.61.0, commit `32c0b2c1d9e11f68da0e6e7b63044e57878590de`. Apache-2.0. Logs data model: https://raw.githubusercontent.com/open-telemetry/opentelemetry-specification/v1.61.0/specification/logs/data-model.md. License: https://raw.githubusercontent.com/open-telemetry/opentelemetry-specification/v1.61.0/LICENSE.
- W3C Trace Context Level 1 Recommendation, 2021-11-23. W3C permissive document license identified by the reference: https://www.w3.org/TR/2021/REC-trace-context-1-20211123/.
- Google SRE troubleshooting methodology: https://sre.google/sre-book/effective-troubleshooting/. Conceptual reference only; no prose/code copied.
- HolmesGPT and Jaeger are overlap references in PLAN.md; neither is a dependency or incorporated component.

The repository LICENSE is the canonical Apache-2.0 text retrieved from https://www.apache.org/licenses/LICENSE-2.0.txt on 2026-10-07. Original source and synthetic data use that license. No Python distribution, model weights, or third-party dataset is distributed.

Prepared CI uses two external GitHub actions, not vendored action code. Their immutable action definitions, READMEs, and licenses were read again 2026-10-08:

- `actions/checkout` v7.0.1, commit `3d3c42e5aac5ba805825da76410c181273ba90b1`, MIT; Copyright (c) 2018 GitHub, Inc. and contributors. [License](https://raw.githubusercontent.com/actions/checkout/3d3c42e5aac5ba805825da76410c181273ba90b1/LICENSE), [source](https://github.com/actions/checkout/tree/3d3c42e5aac5ba805825da76410c181273ba90b1).
- `actions/setup-python` v7.0.0, commit `5fda3b95a4ea91299a34e894583c3862153e4b97`, MIT; Copyright (c) 2018 GitHub, Inc. and contributors. [License](https://raw.githubusercontent.com/actions/setup-python/5fda3b95a4ea91299a34e894583c3862153e4b97/LICENSE), [source](https://github.com/actions/setup-python/tree/5fda3b95a4ea91299a34e894583c3862153e4b97).

No action package, runtime binary, or third-party dataset is redistributed. Original example bundles, expectations, failure profiles, and review scripts are Apache-2.0 repository work. Their provenance is recorded under `examples/`. Hosted CI remains unexecuted; [docs/ci.md](docs/ci.md) records runner/runtime pins, availability observations, and limits.
