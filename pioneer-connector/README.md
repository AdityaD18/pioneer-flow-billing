# Pioneer Tally Connector Service

Standalone REST API microservice built with **FastAPI** to interface between **Pioneer Flow Billing ERP** and **TallyPrime 7.1** via XML over HTTP.

## Project Structure

```text
pioneer-connector/
├── api/
│   └── routes/          # REST API endpoints (health, sync, ledgers, stock, vouchers)
├── tally/
│   ├── xml/             # Tally XML request template builders
│   ├── parser/          # Response XML parsers & schema extractors
│   └── models/          # Strongly-typed Pydantic Tally models
├── services/            # Sync engine, retry manager, validator
├── cache/               # In-memory response caching
├── logs/                # Structured connector logs
├── config/              # Centralized configuration & environment loader
├── tests/               # Pytest suite for connector endpoints
├── main.py              # FastAPI server entrypoint
├── requirements.txt
└── README.md
```

## Running the API Server

```bash
uvicorn main:app --reload --port 8000
```
