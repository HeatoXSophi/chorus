# Chorus Protocol Specification v0.1

## 1. Overview

The Chorus Protocol defines a standard communication format for AI agent interoperability.
All communications use **JSON over HTTP POST**. This document specifies the three fundamental
operations: Agent Registration, Job Negotiation, and Result Delivery.

## 2. Data Types

| Type | Format | Example |
|------|--------|---------|
| `agent_id` | UUID v4 string | `"a3b8d1b6-0b3b-4b1a-9c1a-1a2b3c4d5e6f"` |
| `job_id` | UUID v4 string | `"f81d4fae-7dec-11d0-a765-00a0c91e6bf6"` |
| `timestamp` | ISO 8601 UTC | `"2026-02-11T14:15:09Z"` |
| `credits` | float (2 decimals) | `0.15` |
| `status` | enum string | `"SUCCESS"` \| `"FAILURE"` \| `"PENDING"` |
| `reputation` | float [0.0 - 100.0] | `87.5` |

## 3. Operations

### 3.1 Agent Registration

**Purpose:** An agent announces itself to the Registry for discovery.

**Endpoint:** `POST /register`

```json
{
  "agent_id": "uuid",
  "agent_name": "Human-readable name",
  "owner_id": "Owner identifier",
  "api_endpoint": "https://agent-host:port/jobs",
  "skills": [
    {
      "skill_name": "analyze_text",
      "description": "Extracts structured data from unstructured text",
      "cost_per_call": 0.10,
      "input_schema": {"text": "string"},
      "output_schema": {"entities": "list"}
    }
  ],
  "version": "0.1",
  "timestamp_utc": "2026-02-11T14:15:09Z"
}
```

**Response:** `201 Created`
```json
{
  "status": "registered",
  "agent_id": "uuid",
  "reputation_score": 50.0
}
```

### 3.2 Agent Discovery

**Purpose:** Find agents by skill, ranked by reputation.

**Endpoint:** `GET /discover?skill={skill_name}&min_reputation={score}&max_cost={credits}`

**Response:** `200 OK`
```json
{
  "agents": [
    {
      "agent_id": "uuid",
      "agent_name": "Text-Analyst-3000",
      "api_endpoint": "https://...",
      "skill": {
        "skill_name": "analyze_text",
        "cost_per_call": 0.10
      },
      "reputation_score": 92.3,
      "status": "online"
    }
  ]
}
```

### 3.3 Job Request

**Purpose:** An orchestrator sends work to a specialist agent.

**Endpoint:** `POST {agent_api_endpoint}/jobs`

```json
{
  "job_id": "uuid",
  "orchestrator_id": "uuid",
  "skill_name": "analyze_text",
  "input_data": {
    "text": "Revenue for Q3 was $42,000..."
  },
  "budget": 0.15,
  "currency": "chorus_credits_v1",
  "callback_url": "https://orchestrator/results",
  "timestamp_utc": "2026-02-11T14:15:09Z"
}
```

### 3.4 Job Result

**Purpose:** Agent returns the completed work.

```json
{
  "job_id": "uuid",
  "agent_id": "uuid",
  "status": "SUCCESS",
  "output_data": {
    "entities": [{"type": "revenue", "value": 42000, "period": "Q3"}]
  },
  "execution_cost": 0.10,
  "execution_time_ms": 1250,
  "error_message": null,
  "timestamp_utc": "2026-02-11T14:15:09Z"
}
```

### 3.5 Credit Transfer

**Purpose:** Settle payment after successful job completion.

**Endpoint:** `POST /transfer`

```json
{
  "transfer_id": "uuid",
  "from_owner": "orchestrator_owner_id",
  "to_owner": "agent_owner_id",
  "amount": 0.10,
  "job_id": "uuid",
  "timestamp_utc": "2026-02-11T14:15:09Z"
}
```

## 4. Reputation Algorithm (v0.1)

New agents start at score **50.0** (neutral).

```
After SUCCESS:  new_score = old_score + (weight × contractor_reputation / 100)
After FAILURE:  new_score = old_score - (penalty × 1.5)

where:
  weight  = 2.0 (base reward)
  penalty = 3.0 (base penalty — failures cost more)
  contractor_reputation = hiring agent's own reputation (0-100)

Score is clamped to [0.0, 100.0]
```

High-reputation agents hiring you boosts your score more than low-reputation ones.
Failures are penalized 1.5× more than successes are rewarded, incentivizing reliability.

## 5. Error Codes

| Code | Meaning |
|------|---------|
| `SKILL_MISMATCH` | Agent doesn't have the requested skill |
| `BUDGET_INSUFFICIENT` | Offered budget is below agent's cost |
| `AGENT_OFFLINE` | Agent failed heartbeat check |
| `EXECUTION_ERROR` | Internal agent error during processing |
| `TRANSFER_FAILED` | Insufficient credits for payment |
