from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.models.transaction import TransactionType
from app.services.portfolio_period_service import _quantity_at


def transaction(kind: TransactionType, quantity: float, day: int):
    return SimpleNamespace(
        transaction_type=kind,
        quantity=quantity,
        transaction_date=datetime(2026, 7, day, tzinfo=timezone.utc),
    )


def test_quantity_at_reconstructs_buys_and_sells_after_boundary() -> None:
    transactions = [
        transaction(TransactionType.BUY, 5, 14),
        transaction(TransactionType.SELL, 2, 16),
    ]

    assert _quantity_at(13, transactions, date(2026, 7, 13)) == 10
    assert _quantity_at(13, transactions, date(2026, 7, 15)) == 15
    assert _quantity_at(13, transactions, date(2026, 7, 17)) == 13


def test_quantity_at_handles_fully_sold_position() -> None:
    transactions = [transaction(TransactionType.SELL, 4, 15)]

    assert _quantity_at(0, transactions, date(2026, 7, 14)) == 4
    assert _quantity_at(0, transactions, date(2026, 7, 16)) == 0
