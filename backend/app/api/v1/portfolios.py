"""Portfolio endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.models.database import get_db
from app.models.portfolio import Portfolio, Holding
from app.schemas.portfolio import (
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioResponse,
    PortfolioMetrics,
    RiskMetrics
)
from app.core.security import get_current_user_id
from app.services.portfolio_analysis import PortfolioAnalysisService

router = APIRouter()
analysis_service = PortfolioAnalysisService()


@router.post("/", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    portfolio_data: PortfolioCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a new portfolio"""
    # Validate weights sum to approximately 1.0
    total_weight = sum(h.weight for h in portfolio_data.holdings)
    if not (0.99 <= total_weight <= 1.01):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Holdings weights must sum to 1.0, got {total_weight}"
        )

    # Create portfolio
    portfolio = Portfolio(
        user_id=user_id,
        name=portfolio_data.name,
        description=portfolio_data.description
    )
    db.add(portfolio)
    db.flush()

    # Add holdings
    for holding_data in portfolio_data.holdings:
        holding = Holding(
            portfolio_id=portfolio.id,
            ticker=holding_data.ticker,
            weight=holding_data.weight
        )
        db.add(holding)

    db.commit()
    db.refresh(portfolio)

    return portfolio


@router.get("/", response_model=List[PortfolioResponse])
def list_portfolios(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """List all portfolios for the current user"""
    portfolios = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    return portfolios


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(
    portfolio_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get a specific portfolio"""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user_id
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    return portfolio


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
def update_portfolio(
    portfolio_id: int,
    portfolio_data: PortfolioUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update a portfolio"""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user_id
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    # Update fields
    if portfolio_data.name:
        portfolio.name = portfolio_data.name
    if portfolio_data.description is not None:
        portfolio.description = portfolio_data.description

    # Update holdings if provided
    if portfolio_data.holdings is not None:
        # Validate weights
        total_weight = sum(h.weight for h in portfolio_data.holdings)
        if not (0.99 <= total_weight <= 1.01):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Holdings weights must sum to 1.0, got {total_weight}"
            )

        # Delete existing holdings
        db.query(Holding).filter(Holding.portfolio_id == portfolio_id).delete()

        # Add new holdings
        for holding_data in portfolio_data.holdings:
            holding = Holding(
                portfolio_id=portfolio.id,
                ticker=holding_data.ticker,
                weight=holding_data.weight
            )
            db.add(holding)

    db.commit()
    db.refresh(portfolio)

    return portfolio


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(
    portfolio_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete a portfolio"""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user_id
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    db.delete(portfolio)
    db.commit()


@router.get("/{portfolio_id}/metrics", response_model=PortfolioMetrics)
def get_portfolio_metrics(
    portfolio_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get portfolio performance metrics"""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user_id
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    # Convert holdings to dict format
    holdings = [
        {"ticker": h.ticker, "weight": h.weight}
        for h in portfolio.holdings
    ]

    # Calculate metrics
    metrics = analysis_service.get_portfolio_metrics(holdings)

    return metrics


@router.get("/{portfolio_id}/risk", response_model=RiskMetrics)
def get_risk_metrics(
    portfolio_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get portfolio risk metrics"""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == user_id
    ).first()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )

    # Convert holdings to dict format
    holdings = [
        {"ticker": h.ticker, "weight": h.weight}
        for h in portfolio.holdings
    ]

    # Calculate risk metrics
    risk = analysis_service.get_risk_metrics(holdings)

    return risk
