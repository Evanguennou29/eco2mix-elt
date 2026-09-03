# eco2mix-elt

[![CI](https://github.com/Evanguennou29/eco2mix-elt/actions/workflows/ci.yml/badge.svg)](https://github.com/Evanguennou29/eco2mix-elt/actions/workflows/ci.yml)

A reproducible ELT pipeline answering when French electricity is cleanest.

## The question

At what time should you consume electricity in France to emit the least CO₂ —
and does the answer change by region and by season? This repository ingests
the French grid operator's quarter-hourly public data, models it through
staging and analytical marts, and answers that question with a dashboard, not
just a pile of charts.

## Status

This repository is under active construction. The pitch above is the target;
the pipeline, models, and dashboard described in [`SPEC.md`](SPEC.md) are
being built lot by lot. See `SPEC.md` for the full specification and the
lot-by-lot plan.

## Out of scope

- No forecasting, no machine learning model.
- No real-time streaming: the pipeline runs at a daily cadence.
- No countries other than France, no market or price data.
- No paid cloud deployment: DuckDB as a file, dashboard on a free tier.

## Licence

Code: MIT. Data: see the source licence documented once ingestion lands.
