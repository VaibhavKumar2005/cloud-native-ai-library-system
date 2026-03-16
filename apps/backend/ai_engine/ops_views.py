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
from .promptops import get_prompt_ops
from .evalops import get_eval_ops
from .driftops import get_drift_ops

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


# ============================================================================
# PROMPT OPS ENDPOINTS
# ============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def prompt_versions(request, prompt_name: str) -> Response:
    """
    GET: List all versions of a prompt
    POST: Create new prompt version
    """
    try:
        prompt_ops = get_prompt_ops()
        
        if request.method == 'GET':
            versions = prompt_ops.get_all_versions(prompt_name)
            return Response({
                "status": "success",
                "prompt_name": prompt_name,
                "versions": versions,
                "count": len(versions),
            })
        
        elif request.method == 'POST':
            data = request.data
            version = prompt_ops.create_version(
                prompt_name=prompt_name,
                system_prompt=data['system_prompt'],
                user_prompt_template=data['user_prompt_template'],
                temperature=data.get('temperature', 0.7),
                max_tokens=data.get('max_tokens', 2048),
                top_p=data.get('top_p', 0.95),
                tags=data.get('tags', []),
            )
            
            return Response({
                "status": "success",
                "version": version,
                "message": "Prompt version created",
            }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        logger.error(f"Error in prompt versions: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60)
def prompt_active(request, prompt_name: str) -> Response:
    """Get the current active prompt version."""
    try:
        prompt_ops = get_prompt_ops()
        active = prompt_ops.get_active_version(prompt_name)
        
        if not active:
            return Response(
                {"status": "error", "message": "No active version found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        return Response({
            "status": "success",
            "prompt_name": prompt_name,
            "active_version": active,
        })
    
    except Exception as e:
        logger.error(f"Error getting active prompt: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def prompt_promote(request) -> Response:
    """Promote a prompt version to active."""
    try:
        prompt_ops = get_prompt_ops()
        data = request.data
        
        result = prompt_ops.promote_to_active(
            prompt_name=data['prompt_name'],
            version_id=data['version_id'],
        )
        
        if not result:
            return Response(
                {"status": "error", "message": "Failed to promote version"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        return Response({
            "status": "success",
            "message": f"Version {data['version_id']} promoted to active",
        })
    
    except Exception as e:
        logger.error(f"Error promoting prompt: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def prompt_ab_tests(request) -> Response:
    """
    GET: List A/B tests
    POST: Create new A/B test
    """
    try:
        prompt_ops = get_prompt_ops()
        
        if request.method == 'GET':
            tests = prompt_ops.list_ab_tests()
            return Response({
                "status": "success",
                "tests": tests,
                "count": len(tests),
            })
        
        elif request.method == 'POST':
            data = request.data
            test = prompt_ops.create_ab_test(
                prompt_name=data['prompt_name'],
                variant_a_version_id=data['variant_a_version_id'],
                variant_b_version_id=data['variant_b_version_id'],
                split_ratio=data.get('split_ratio', 0.5),
                duration_days=data.get('duration_days', 7),
            )
            
            return Response({
                "status": "success",
                "test": test,
                "message": "A/B test created",
            }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        logger.error(f"Error in A/B tests: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def prompt_ab_results(request, test_id: str) -> Response:
    """Get results of a specific A/B test."""
    try:
        prompt_ops = get_prompt_ops()
        results = prompt_ops.get_test_results(test_id)
        
        if not results:
            return Response(
                {"status": "error", "message": "Test not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        return Response({
            "status": "success",
            "test_id": test_id,
            "results": results,
        })
    
    except Exception as e:
        logger.error(f"Error getting test results: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================================
# EVAL OPS ENDPOINTS
# ============================================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def eval_datasets(request) -> Response:
    """
    GET: List all test datasets
    POST: Create new dataset
    """
    try:
        eval_ops = get_eval_ops()
        
        if request.method == 'GET':
            datasets = eval_ops.list_datasets()
            return Response({
                "status": "success",
                "datasets": [
                    {
                        "dataset_id": d.dataset_id,
                        "name": d.name,
                        "description": d.description,
                        "question_count": len(d.queries),
                        "tags": d.tags,
                        "created_at": d.created_at,
                    }
                    for d in datasets
                ],
                "count": len(datasets),
            })
        
        elif request.method == 'POST':
            data = request.data
            dataset = eval_ops.create_dataset(
                name=data['name'],
                queries=data['queries'],
                expected_answers=data['expected_answers'],
                context_sources=data['context_sources'],
                description=data.get('description', ''),
                tags=data.get('tags', []),
            )
            
            return Response({
                "status": "success",
                "dataset": {
                    "dataset_id": dataset.dataset_id,
                    "name": dataset.name,
                    "question_count": len(dataset.queries),
                },
                "message": "Dataset created",
            }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        logger.error(f"Error in eval datasets: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def eval_runs(request) -> Response:
    """
    GET: List evaluation runs
    POST: Create new evaluation run
    """
    try:
        eval_ops = get_eval_ops()
        
        if request.method == 'GET':
            dataset_id = request.query_params.get('dataset_id')
            runs = eval_ops.list_eval_runs(dataset_id=dataset_id)
            return Response({
                "status": "success",
                "runs": runs,
                "count": len(runs),
            })
        
        elif request.method == 'POST':
            data = request.data
            run = eval_ops.create_eval_run(
                dataset_id=data['dataset_id'],
                prompt_version_id=data['prompt_version_id'],
                model=data.get('model', 'gpt-4-turbo'),
            )
            
            return Response({
                "status": "success",
                "run": {
                    "run_id": run.run_id,
                    "dataset_id": run.dataset_id,
                    "status": run.status,
                    "total_questions": run.total_questions,
                },
                "message": "Evaluation run started",
            }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        logger.error(f"Error in eval runs: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def eval_run_summary(request, run_id: str) -> Response:
    """Get summary of a specific evaluation run."""
    try:
        eval_ops = get_eval_ops()
        summary = eval_ops.get_run_summary(run_id)
        
        if not summary:
            return Response(
                {"status": "error", "message": "Run not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        return Response({
            "status": "success",
            "run": summary,
        })
    
    except Exception as e:
        logger.error(f"Error getting eval run: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ============================================================================
# DRIFT OPS ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(60)
def drift_summary(request) -> Response:
    """Get drift monitoring summary."""
    try:
        drift_ops = get_drift_ops()
        summary = drift_ops.get_drift_summary()
        
        return Response({
            "status": "success",
            "drift": summary,
        })
    
    except Exception as e:
        logger.error(f"Error getting drift summary: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def drift_alerts(request) -> Response:
    """Get recent drift alerts."""
    try:
        drift_ops = get_drift_ops()
        minutes = int(request.query_params.get('minutes', '60'))
        severity = request.query_params.get('severity')
        
        alerts = drift_ops.get_recent_alerts(minutes=minutes, severity=severity)
        
        return Response({
            "status": "success",
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "timestamp": a.timestamp,
                    "drift_type": a.drift_type,
                    "severity": a.severity,
                    "description": a.description,
                    "baseline_value": a.baseline_value,
                    "current_value": a.current_value,
                    "acknowledged": a.acknowledged,
                }
                for a in alerts
            ],
            "count": len(alerts),
        })
    
    except Exception as e:
        logger.error(f"Error getting drift alerts: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def drift_acknowledge_alert(request, alert_id: str) -> Response:
    """Mark a drift alert as acknowledged."""
    try:
        drift_ops = get_drift_ops()
        success = drift_ops.acknowledge_alert(alert_id)
        
        if not success:
            return Response(
                {"status": "error", "message": "Failed to acknowledge alert"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        return Response({
            "status": "success",
            "message": f"Alert {alert_id} acknowledged",
        })
    
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
