"""
Chorus Ledger — Economic layer for credit management and auditing.

Tracks balances, processes transfers, and maintains an immutable
audit log of all transactions in the ecosystem.
"""

from __future__ import annotations

from chorus.models import TransferRecord, ErrorCode, _uuid, _now


class InsufficientCreditsError(Exception):
    """Raised when an owner doesn't have enough credits for a transfer."""
    pass


class Ledger:
    """
    In-memory ledger that manages credits and transaction history.
    
    Every transfer is atomic and recorded in an append-only audit log.
    """

    def __init__(self):
        self._balances: dict[str, float] = {}  # owner_id -> balance
        self._audit_log: list[TransferRecord] = []
        self._total_volume: float = 0.0

    def create_account(self, owner_id: str, initial_balance: float = 100.0) -> float:
        """Create an account with an initial credit balance."""
        if owner_id not in self._balances:
            self._balances[owner_id] = initial_balance
        return self._balances[owner_id]

    def get_balance(self, owner_id: str) -> float:
        """Get the current balance for an owner."""
        return self._balances.get(owner_id, 0.0)

    def transfer(self, from_owner: str, to_owner: str, amount: float, job_id: str) -> TransferRecord:
        """
        Execute an atomic credit transfer between two owners.
        
        Args:
            from_owner: The payer's owner ID
            to_owner: The payee's owner ID
            amount: Credits to transfer (must be > 0)
            job_id: Associated job ID for audit purposes
            
        Returns:
            TransferRecord documenting the transaction
            
        Raises:
            InsufficientCreditsError: If payer doesn't have enough credits
            ValueError: If amount <= 0
        """
        if amount <= 0:
            raise ValueError(f"Transfer amount must be positive, got {amount}")

        # Ensure accounts exist
        if from_owner not in self._balances:
            raise InsufficientCreditsError(
                f"Account '{from_owner}' does not exist"
            )

        if self._balances[from_owner] < amount:
            raise InsufficientCreditsError(
                f"'{from_owner}' has {self._balances[from_owner]:.2f} credits, "
                f"needs {amount:.2f}"
            )

        # Ensure payee account exists
        if to_owner not in self._balances:
            self._balances[to_owner] = 0.0

        # Atomic transfer
        self._balances[from_owner] -= amount
        self._balances[to_owner] += amount
        self._total_volume += amount

        # Record in audit log
        record = TransferRecord(
            from_owner=from_owner,
            to_owner=to_owner,
            amount=amount,
            job_id=job_id,
        )
        self._audit_log.append(record)
        return record

    def get_audit_log(self, job_id: str | None = None, owner_id: str | None = None) -> list[TransferRecord]:
        """
        Query the audit log.
        
        Args:
            job_id: Filter by specific job
            owner_id: Filter by owner (as sender or receiver)
        """
        results = self._audit_log

        if job_id:
            results = [r for r in results if r.job_id == job_id]

        if owner_id:
            results = [r for r in results if r.from_owner == owner_id or r.to_owner == owner_id]

        return results

    def get_all_balances(self) -> dict[str, float]:
        """Get all account balances."""
        return dict(self._balances)

    def get_total_volume(self) -> float:
        """Get total transaction volume across all transfers."""
        return self._total_volume

    def get_transaction_count(self) -> int:
        """Total number of recorded transactions."""
        return len(self._audit_log)
