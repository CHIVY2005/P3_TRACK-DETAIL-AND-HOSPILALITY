# Guardian Pricing OS - Codebase Documentation

Tai lieu nay la ban tong hop chinh thuc cua codebase cho P3. Cac tai lieu chi tiet van duoc giu lai de phuc vu pitch, QA va deploy; file nay la diem vao duy nhat de doc kien truc, van hanh va cac metric ma he thong dang hien thi.

## 1. Product Thesis

Guardian Pricing OS bien du lieu gia doi thu thanh quy trinh ra quyet dinh co the kiem tra:

```text
Ingest -> Discover -> Scrape -> Validate -> Analyze -> Recommend -> Approve
```

MVP tap trung vao bai toan P3: theo doi CPI, bao ve margin va tao action cho Commercial Team. Pricing logic hien la rule-based/template de giai thich ro voi giam khao; LLM/RAG khong nam trong duong quyet dinh gia.

## 2. Repository Map

```text
backend/app/
  agents/       Orchestrator, Market Observer, Margin Guardian, Supplier Negotiator
  db/           SQLAlchemy engine, session, models
  routes/       REST API boundary
  scraper/      Apify, Playwright, Crawl4AI va fixture fallback
  services/     ingestion, discovery, channel intelligence, quality, KPI, scheduler
  main.py       FastAPI lifecycle va router registration

frontend/src/
  pages/        Overview, Product Insights, Agent Workspace, Configuration
  App.jsx       application shell va navigation
  index.css     Guardian visual system

backend/tests/  API, decision, ingestion, runtime, data-quality va KPI tests
docs/           architecture, demo, QA, deployment va changelog
```

## 3. Runtime Architecture

```text
React Dashboard
  |  /api/v1/products, pricing, alerts, scraper, agent, sync
  v
FastAPI Routes
  |
  +--> SQLite default / PostgreSQL optional
  +--> Dynamic Ingestion -> Product + CompetitorLink
  +--> Link Discovery -> search-driven competitor URL
  +--> Hybrid Scraper -> CompetitorPrice + raw evidence
  +--> CPI Calculator -> PricingIndex + Alert
  +--> Agent Runtime -> AgentTask + AgentAction
  +--> Langfuse -> trace/span/tool observability
```

### Database entities

- `Product`: catalog, Guardian price and cost price.
- `CompetitorLink`: platform URL and discovery method.
- `CompetitorPrice`: raw/net price, promotion, stock, anomaly flag and timestamp.
- `PricingIndex`: CPI and recommendation per SKU.
- `Alert`: unresolved commercial signal.
- `AgentTask`: one autonomous decision cycle.
- `AgentAction`: approval-gated price alignment or supplier draft.

## 4. Agent Architecture

### Orchestrator

Entry point: `backend/app/agents/orchestrator/agent_orchestrator.py`.

It opens a run, asks Market Observer for signals, ranks unresolved alerts, invokes Margin Guardian, persists actions, and closes the cycle.

### Market Observer

Entry point: `backend/app/agents/market_observer/market_observer_agent.py`.

It is a real runtime stage, not a placeholder. It can execute:

- `refresh_competitor_market`: inspect products, discover links, scrape and normalize observations.
- `load_latest_market_signals`: reuse persisted observations when live refresh is disabled.

The scraper reports progress per SKU to the Agent Workspace.

### Margin Guardian

Entry point: `backend/app/agents/margin_guardian/margin_guardian_agent.py`.

It computes current margin and margin-after-match, then applies the configured minimum margin rule:

```text
margin_after_match >= minimum_margin -> match proposal
margin_after_match < minimum_margin  -> supplier negotiation
```

### Supplier Negotiator

Entry point: `backend/app/agents/supplier_negotiator/supplier_negotiator_agent.py`.

It uses rule/template tools to query the supplier policy context and generate a cost-protection draft. It does not require RAG to make a pricing decision.

## 5. Data Quality And Confidence

Service: `backend/app/services/data_quality.py`.

Every SKU decision receives an evidence score from observable data:

| Component | Weight | Meaning |
|---|---:|---|
| Channel coverage | 35% | How many configured competitor channels have a latest observation |
| Validity | 30% | Share of observations that are in stock, positive and not suspicious |
| Freshness | 25% | Share of configured channels inside the freshness SLA |
| Link coverage | 10% | Share of configured channels with a mapped competitor link |

Confidence labels are deterministic:

- `High`: score >= 80
- `Medium`: score >= 60
- `Low`: score < 60

This score is shown in the priority queue and returned in `GET /api/v1/agent/briefing` as:

- `data_quality_pct`
- `confidence_label`
- `data_quality_reasons`

The score is evidence confidence, not model confidence and not a claim that a price action is guaranteed to succeed.

## 6. Business KPI Scorecard

Service: `backend/app/services/business_kpis.py`.

Endpoint: `GET /api/v1/agent/kpis`.

The Overview page surfaces:

- `average_decision_confidence_pct`: evidence quality of the active decision queue.
- `estimated_margin_exposure_vnd`: current Guardian-to-competitor price-gap value under review.
- `estimated_protected_exposure_vnd`: portion routed to supplier negotiation because matching would cross the margin floor.
- `alignment_opportunity_vnd`: upward price-alignment opportunity when the market reference is higher and margin remains safe.
- `recommendation_acceptance_pct`: approved/executed actions divided by reviewed actions.
- `decision_coverage_pct`: active alerts with a usable decision context.
- `automated_coverage_pct`, `fresh_observation_pct`, `valid_observation_pct`: evidence readiness.
- `completed_cycles` and `latest_cycle_duration_seconds`: operational throughput.

The exposure fields are explicitly estimates. They are not reported as realized savings until a human-approved action has been persisted and executed.

## 7. End-To-End Workflow

1. Upload CSV/JSON through `POST /api/v1/products/import-dataset`.
2. Normalize aliases into `Product` records.
3. Create explicit `CompetitorLink` records or search-driven links when URLs are missing.
4. Scrape through Apify, Playwright or Crawl4AI; use deterministic fallback fixtures when the environment blocks network access.
5. Store raw/clean observations in `CompetitorPrice`.
6. Reject suspicious, unavailable or stale evidence from decision contexts.
7. Calculate CPI and generate alerts.
8. Run the daily scheduler or manual Agent Workspace trigger.
9. Route each alert through Margin Guardian.
10. Persist `AgentAction` as pending human approval.
11. Approve/reject from the dashboard and recalculate CPI after approved price alignment.

## 8. Observability

Langfuse records:

- root agent runtime span
- pricing cycle span
- per-alert pricing span
- tool observations for calculations, scraping and supplier drafting
- approval/rejection spans

The local Agent Workspace additionally polls `GET /api/v1/agent/runtime-status` every second and shows:

- active agent and phase
- current tool and status
- current SKU and progress
- audit-safe reasoning summary
- four-agent roster
- recent tool events
- execution timeline

The UI does not expose hidden chain-of-thought. It exposes short, evidence-backed rationale suitable for audit and judging.

## 9. Persistence And Deployment

Default local mode uses `backend/guardian.db` with SQLite. This keeps a fresh clone runnable without PostgreSQL. PostgreSQL remains supported by setting `USE_SQLITE=False` and providing database variables.

For the hackathon:

```text
Backend:  http://127.0.0.1:8001
Frontend: http://127.0.0.1:3000
Swagger:  http://127.0.0.1:8001/docs
```

The daily scheduler defaults to `86400` seconds. It is an in-process thread for the MVP; production deployment should move scheduling to a durable worker/queue and use Redis or another shared runtime store for multi-process live state.

## 10. Demo Narrative

Recommended judging sequence:

1. Open Pricing Command and show six-channel coverage, freshness and business scorecard.
2. Open a priority SKU and point out the evidence confidence and reason.
3. Start the decision cycle from Agent Workspace.
4. Show Market Observer scanning a SKU and the tool timeline changing.
5. Show Margin Guardian comparing margin-after-match with the floor.
6. Show Supplier Negotiator drafting a cost-protection action when matching is unsafe.
7. Approve one safe price-alignment action and explain that the alert is resolved only after human approval.
8. Open the Langfuse trace to show the same orchestration and tool evidence externally.

## 11. Verification

The current repository verification suite includes:

- API and domain tests
- ingestion and mapping tests
- agent decision tests
- live runtime timeline tests
- product data-quality tests
- business KPI tests
- frontend production build

Run locally:

```powershell
cd backend
..\.venv312\Scripts\python.exe -m pytest -q

cd ..\frontend
npm.cmd run build
```

## 12. Honest Production Risks

- Scraping 200 live SKUs needs per-channel rate limits, retries, anti-bot handling and connector monitoring.
- The scheduler is still process-local and should become a durable worker job.
- Live runtime state is process-local; multiple API workers need shared state.
- No authentication or role-based approval policy is included in the hackathon MVP.
- SQLite is suitable for the demo and single-process mode, not high-concurrency production writes.

## 13. Detailed Documents

- [CODEBASE_GUIDE.md](../CODEBASE_GUIDE.md) - ownership and module map.
- [TECHNICAL_EXPLANATION.md](../TECHNICAL_EXPLANATION.md) - technical walkthrough.
- [END_TO_END_WORKFLOW.md](END_TO_END_WORKFLOW.md) - complete data lifecycle.
- [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) - architecture visuals.
- [AGENTS_GUIDE.md](AGENTS_GUIDE.md) - agent responsibilities and tools.
- [JUDGE_DEMO_RUNBOOK.md](JUDGE_DEMO_RUNBOOK.md) - live judging sequence.
- [QA_GUIDE.md](QA_GUIDE.md) - verification and troubleshooting.
- [CONFIG_AND_DEPLOY_GUIDE.md](CONFIG_AND_DEPLOY_GUIDE.md) - local and deployment configuration.
- [TOP5_COMPETITION_STRATEGY.md](TOP5_COMPETITION_STRATEGY.md) - differentiation strategy.
- [CHANGELOG_UPDATE_2026-07-11.md](CHANGELOG_UPDATE_2026-07-11.md) - latest implementation changelog.
