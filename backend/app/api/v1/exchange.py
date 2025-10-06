"""
Exchange rate API endpoints.
"""
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from app.services.exchange_rate_service import get_exchange_rate_service

router = APIRouter()


@router.get("/rate")
async def get_exchange_rate(
    from_currency: str = Query(..., description="Source currency code (e.g., USD)", regex="^[A-Z]{3}$"),
    to_currency: str = Query(..., description="Target currency code (e.g., CAD)", regex="^[A-Z]{3}$"),
    use_cache: bool = Query(True, description="Whether to use cached rates")
) -> Any:
    """
    Get current exchange rate between two currencies.

    Args:
        from_currency: Source currency code (3 letters, e.g., USD)
        to_currency: Target currency code (3 letters, e.g., CAD)
        use_cache: Whether to use cached rates (default: True)

    Returns:
        Exchange rate information including rate, timestamp, and source
    """
    try:
        service = get_exchange_rate_service()
        rate_info = await service.get_rate_info(from_currency, to_currency)

        return {
            "success": True,
            "data": rate_info
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch exchange rate: {str(e)}"
        )


@router.post("/convert")
async def convert_amount(
    amount: float = Query(..., description="Amount to convert", gt=0),
    from_currency: str = Query(..., description="Source currency code", regex="^[A-Z]{3}$"),
    to_currency: str = Query(..., description="Target currency code", regex="^[A-Z]{3}$"),
    use_cache: bool = Query(True, description="Whether to use cached rates")
) -> Any:
    """
    Convert an amount from one currency to another.

    Args:
        amount: Amount to convert
        from_currency: Source currency code (3 letters)
        to_currency: Target currency code (3 letters)
        use_cache: Whether to use cached rates

    Returns:
        Converted amount with exchange rate details
    """
    try:
        service = get_exchange_rate_service()

        # Get rate info
        rate_info = await service.get_rate_info(from_currency, to_currency)

        # Convert amount
        converted_amount = await service.convert_amount(
            amount,
            from_currency,
            to_currency,
            use_cache
        )

        return {
            "success": True,
            "data": {
                "original_amount": amount,
                "original_currency": from_currency.upper(),
                "converted_amount": converted_amount,
                "converted_currency": to_currency.upper(),
                "exchange_rate": rate_info["rate"],
                "timestamp": rate_info["timestamp"]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to convert amount: {str(e)}"
        )


@router.get("/supported-currencies")
async def get_supported_currencies() -> Any:
    """
    Get list of supported currencies.

    Returns:
        List of supported currency codes
    """
    return {
        "success": True,
        "data": {
            "currencies": ["USD", "CAD"],
            "default": "USD"
        }
    }
