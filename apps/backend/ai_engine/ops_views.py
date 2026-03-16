"""
VeriRAG Operations Dashboard Views
REST API endpoints for CostOps and QualityOps metrics and dashboards.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.cache import cache_page
from django.core.cache import cache

from .costops import get_cost_tracker
from .qualityops import get_quality_gate

logger = logging.getLogger(__name__)


# ============================================================================
# COST OPS ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60)  # Cache for 60 seconds
def cost_metrics_today(request) -> Response:
    """
    Get cost metrics for today.
    
    Returns:
        {
            "status": "success",
            "period": "last_1_days",
            "metrics": {
                "total_cost": 12.45,
                "total_tokens": 45000,
                "requests_count": 123,
                "most_expensive_operation": "rag_query",
                "cost_by_operation": {...},
                "budget_remaining": 987.55,
                "budget_utilization_percent": 1.25
            }
        }
    """
    try:
        tracker = get_cost_tracker()
        metrics = tracker.get_metrics(days=1)
        
        return Response({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "period": metrics.period,
            "metrics": {
                "total_cost": metrics.total_cost,
                "total_tokens": metrics.total_tokens,
                "avg_cost_per_request": metrics.avg_cost_per_request,
                "requests_count": metrics.requests_count,
                "most_expensive_operation": metrics.most_expensive_operation,
                "tokens_by_model": metrics.tokens_by_model,
                "cost_by_operation": metrics.cost_by_operation,
                "budget_remaining": metrics.budget_remaining,
                "budget_utilization_percent": metrics.budget_utilization_percent,
            },
        })
    except Exception as e:
        logger.error(f"Error fetching cost metrics: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(300)  # Cache for 5 minutes
def cost_metrics_week(request) -> Response:
    """Get cost metrics for the past 7 days."""
    try:
        tracker = get_cost_tracker()
        metrics = tracker.get_metrics(days=7)
        
        return Response({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "period": metrics.period,
            "metrics": {
                "total_cost": metrics.total_cost,
                "total_tokens": metrics.total_tokens,
                "avg_cost_per_request": metrics.avg_cost_per_request,
                "requests_count": metrics.requests_count,
                "budget_utilization_percent": metrics.budget_utilization_percent,
            },
        })
    except Exception as e:
        logger.error(f"Error fetching week cost metrics: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def budget_alert(request) -> Response:
    """
    Check if any budget alerts are active.
    
    Returns:
        {
            "status": "success",
            "alert_active": true/false,
            "alert": {...} or null
        }
    """
    try:
        tracker = get_cost_tracker()
        alert = tracker.check_budget_alert()
        
        return Response({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "alert_active": alert is not None,
            "alert": alert,
        })
    except Exception as e:
        logger.error(f"Error checking budget alert: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================================
# QUALITY OPS ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(300)  # Cache for 5 minutes
def quality_metrics_week(request) -> Response:
    """
    Get quality metrics for the past 7 days.
    
    Returns:
        {
            "status": "success",
            "metrics": {
                "total_evaluations": 234,
                "average_score": 0.82,
                "tier_distribution": {...},
                "component_averages": {...},
                "components_passing_percent": 87.2,
                "trending": "improving",
                "critical_issues": []
            }
        }
    """
    try:
        gate = get_quality_gate()
        metrics = gate.get_quality_metrics(days=7)
        
        return Response({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "total_evaluations": metrics.total_evaluations,
                "average_score": metrics.average_score,
                "tier_distribution": metrics.tier_distribution,
                "component_averages": metrics.component_averages,
                "components_passing_percent": metrics.components_passing_percent,
                "trending": metrics.trending,
                "critical_issues": metrics.critical_issues,
            },
        })
    except Exception as e:
        logger.error(f"Error fetching quality metrics: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60)  # Cache for 60 seconds
def quality_metrics_month(request) -> Response:
    """Get quality metrics for the past 30 days."""
    try:
        gate = get_quality_gate()
        metrics = gate.get_quality_metrics(days=30)
        
        return Response({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "period": metrics.period,
            "metrics": {
                "total_evaluations": metrics.total_evaluations,
                "average_score": metrics.average_score,
                "tier_distribution": metrics.tier_distribution,
                "components_passing_percent": metrics.components_passing_percent,
                "trending": metrics.trending,
            },
        })
    except Exception as e:
        logger.error(f"Error fetching month quality metrics: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================================
# UNIFIED OPS DASHBOARD
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60)  # Cache for 60 seconds
def ops_dashboard(request) -> Response:
    """
    Unified dashboard combining Cost + Quality metrics.
    
    Perfect for monitoring both operational and quality KPIs in one request.
    """
    try:
        # Cost metrics
        cost_tracker = get_cost_tracker()
        cost_today = cost_tracker.get_metrics(days=1)
        cost_week = cost_tracker.get_metrics(days=7)
        budget_alert = cost_tracker.check_budget_alert()
        
        # Quality metrics
        quality_gate = get_quality_gate()
        quality_week = quality_gate.get_quality_metrics(days=7)
        quality_month = quality_gate.get_quality_metrics(days=30)
        
        return Response({
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "cost": {
                "today": {
                    "total_cost": cost_today.total_cost,
                    "requests": cost_today.requests_count,
                    "budget_utilization": cost_today.budget_utilization_percent,
                    "budget_remaining": cost_today.budget_remaining,
                },
                "week": {
                    "total_cost": cost_week.total_cost,
                    "requests": cost_week.requests_count,
                    "avg_cost_per_request": cost_week.avg_cost_per_request,
                },
                "alert": budget_alert,
            },
            "quality": {
                "week": {
                    "average_score": quality_week.average_score,
                    "evaluations": quality_week.total_evaluations,
                    "components_passing": quality_week.components_passing_percent,
                    "trending": quality_week.trending,
                },
                "month": {
                    "average_score": quality_month.average_score,
                    "evaluations": quality_month.total_evaluations,
                    "trending": quality_month.trending,
                },
                "critical_issues": quality_week.critical_issues,
            },
            "health": {
                "cost_ops_enabled": cost_tracker.enabled,
                "quality_ops_enabled": quality_gate.enabled,
                "overall_status": "healthy" if not budget_alert and not quality_week.critical_issues else "warning",
            },
        })
    except Exception as e:
        logger.error(f"Error fetching ops dashboard: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
