from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import User, Goal
from backend.auth.dependencies import get_current_user
from backend.engine import project_goal_completion
from backend.schemas import (
    GoalCreateRequest,
    GoalUpdateRequest,
    GoalResponse,
    GoalWithProjectionResponse,
    GoalProjection,
)

router = APIRouter(tags=["Goals"])


@router.get("/goals", response_model=List[GoalResponse], summary="List User Goals")
@router.get("/api/v1/goals", response_model=List[GoalResponse], include_in_schema=False)
def list_goals(
    user_id: Optional[int] = Query(None, description="Optional legacy demo user ID (overridden by authenticated JWT identity)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[GoalResponse]:
    """
    Retrieves all financial goals belonging to the authenticated user.
    """
    authoritative_user_id = current_user.id

    goals = (
        db.query(Goal)
        .filter(Goal.user_id == authoritative_user_id)
        .order_by(Goal.id.asc())
        .all()
    )
    return [GoalResponse.model_validate(g) for g in goals]


@router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED, summary="Create Goal")
@router.post("/api/v1/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_goal(
    payload: GoalCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    """
    Creates a new financial goal with Decimal-safe validation for the authenticated user.
    """
    authoritative_user_id = current_user.id

    if payload.target_amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_amount must be greater than zero.",
        )

    if payload.monthly_contribution <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="monthly_contribution must be greater than zero.",
        )

    new_goal = Goal(
        user_id=authoritative_user_id,
        name=payload.name,
        target_amount=payload.target_amount,
        current_amount=Decimal("0.00"),
        monthly_contribution=payload.monthly_contribution,
        currency="INR",
        target_date=payload.target_date,
        status="active",
    )
    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)

    return GoalResponse.model_validate(new_goal)


@router.patch("/goals/{id}", response_model=GoalWithProjectionResponse, summary="Update Goal Contribution & Project")
@router.patch("/api/v1/goals/{id}", response_model=GoalWithProjectionResponse, include_in_schema=False)
def update_goal_contribution(
    id: int,
    payload: GoalUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalWithProjectionResponse:
    """
    Updates the monthly contribution for an existing goal and returns the updated goal
    along with its deterministic completion projection from project_goal_completion().
    """
    authoritative_user_id = current_user.id

    goal = db.query(Goal).filter(Goal.id == id).first()
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal with id {id} not found.",
        )

    # Strict user isolation check against authenticated current_user
    if goal.user_id != authoritative_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Goal {id} does not belong to authenticated user.",
        )

    if payload.monthly_contribution <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="monthly_contribution must be greater than zero.",
        )

    goal.monthly_contribution = payload.monthly_contribution
    db.commit()
    db.refresh(goal)

    # Compute projection using the deterministic financial engine
    projection_data = project_goal_completion(goal.id, db)

    return GoalWithProjectionResponse(
        goal=GoalResponse.model_validate(goal),
        projection=GoalProjection(
            current_months_remaining=projection_data["current_months_remaining"],
            hypothetical_months_remaining=projection_data.get("hypothetical_months_remaining"),
        ),
    )

