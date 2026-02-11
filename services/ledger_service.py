"""
===================================================================
  🎵 CHORUS — Ledger Service (Phase 1 Network Alpha)
===================================================================

FastAPI microservice for credit management, transfers, and auditing.
Manages the economic layer of the Chorus ecosystem.

Run: uvicorn services.ledger_service:app --port 8002
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from chorus.models import TransferRecord, _uuid, _now


# =============================================================================
# App & State
# =============================================================================

app = FastAPI(
    title="🎵 Chorus Ledger Service",
    description="Credit management, transfers, and transaction auditing for the Chorus network",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state
_balances: dict[str, float] = {}
_audit_log: list[TransferRecord] = []
_total_volume: float = 0.0


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateAccountRequest(BaseModel):
    owner_id: str
    initial_balance: float = Field(default=100.0, ge=0.0)


class TransferRequest(BaseModel):
    from_owner: str
    to_owner: str
    amount: float = Field(..., gt=0)
    job_id: str


class AccountResponse(BaseModel):
    owner_id: str
    balance: float


# =============================================================================
# Endpoints
# =============================================================================

@app.post("/accounts", response_model=AccountResponse, status_code=201)
async def create_account(request: CreateAccountRequest):
    """Create a new account with initial credits."""
    if request.owner_id not in _balances:
        _balances[request.owner_id] = request.initial_balance
    return AccountResponse(
        owner_id=request.owner_id,
        balance=_balances[request.owner_id],
    )


@app.get("/accounts/{owner_id}", response_model=AccountResponse)
async def get_balance(owner_id: str):
    """Get the current balance for an account."""
    if owner_id not in _balances:
        raise HTTPException(status_code=404, detail=f"Account '{owner_id}' not found")
    return AccountResponse(owner_id=owner_id, balance=_balances[owner_id])


@app.post("/transfer", response_model=dict)
async def execute_transfer(request: TransferRequest):
    """Execute an atomic credit transfer between two accounts."""
    global _total_volume

    if request.from_owner not in _balances:
        raise HTTPException(status_code=404, detail=f"Sender '{request.from_owner}' not found")

    if _balances[request.from_owner] < request.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient credits: {_balances[request.from_owner]:.2f} < {request.amount:.2f}",
        )

    # Ensure receiver exists
    if request.to_owner not in _balances:
        _balances[request.to_owner] = 0.0

    # Atomic transfer
    _balances[request.from_owner] -= request.amount
    _balances[request.to_owner] += request.amount
    _total_volume += request.amount

    record = TransferRecord(
        from_owner=request.from_owner,
        to_owner=request.to_owner,
        amount=request.amount,
        job_id=request.job_id,
    )
    _audit_log.append(record)

    return {
        "status": "completed",
        "transfer": record.model_dump(),
        "sender_balance": _balances[request.from_owner],
        "receiver_balance": _balances[request.to_owner],
    }


@app.get("/audit")
async def get_audit_log(
    job_id: str | None = Query(None),
    owner_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """Query the immutable transaction audit log."""
    results = _audit_log

    if job_id:
        results = [r for r in results if r.job_id == job_id]
    if owner_id:
        results = [r for r in results if r.from_owner == owner_id or r.to_owner == owner_id]

    return {
        "transactions": [r.model_dump() for r in results[-limit:]],
        "total": len(results),
    }


@app.get("/economy")
async def economy_stats():
    """Get overall economic statistics for the network."""
    return {
        "total_accounts": len(_balances),
        "total_volume": round(_total_volume, 2),
        "total_transactions": len(_audit_log),
        "all_balances": {k: round(v, 2) for k, v in sorted(_balances.items())},
    }


@app.get("/health")
async def health():
    return {
        "service": "chorus-ledger",
        "status": "healthy",
        "total_accounts": len(_balances),
        "total_transactions": len(_audit_log),
    }
