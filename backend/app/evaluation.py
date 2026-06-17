from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from app.models import EvaluationMetric

def log_evaluation_metric(
    db: Session,
    user_query: str,
    sql_generated: str | None,
    sql_success: bool,
    latency_ms: int,
    is_empty_result: bool,
    user_satisfaction: int | None = None
) -> EvaluationMetric:
    """
    Saves a query evaluation run to the database.
    """
    metric = EvaluationMetric(
        timestamp=datetime.utcnow(),
        user_query=user_query,
        sql_generated=sql_generated,
        sql_success=sql_success,
        latency_ms=latency_ms,
        is_empty_result=is_empty_result,
        user_satisfaction=user_satisfaction
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric

def get_evaluation_summary(db: Session) -> dict:
    """
    Returns aggregated metrics showing system performance.
    """
    total_queries = db.query(EvaluationMetric).count()
    if total_queries == 0:
        return {
            "total_queries": 0,
            "sql_success_rate": 100.0,
            "avg_latency_ms": 0,
            "empty_result_rate": 0.0,
            "avg_satisfaction": 0.0,
            "satisfaction_count": 0
        }
        
    successful_queries = db.query(EvaluationMetric).filter(EvaluationMetric.sql_success == True).count()
    sql_success_rate = (successful_queries / total_queries) * 100
    
    avg_latency = db.query(func.avg(EvaluationMetric.latency_ms)).scalar() or 0
    
    empty_results = db.query(EvaluationMetric).filter(EvaluationMetric.is_empty_result == True).count()
    empty_result_rate = (empty_results / total_queries) * 100
    
    satisfaction_query = db.query(
        func.avg(EvaluationMetric.user_satisfaction),
        func.count(EvaluationMetric.user_satisfaction)
    ).filter(EvaluationMetric.user_satisfaction.isnot(None)).first()
    
    avg_sat = float(satisfaction_query[0]) if satisfaction_query[0] is not None else 0.0
    sat_count = int(satisfaction_query[1]) if satisfaction_query[1] is not None else 0
    
    return {
        "total_queries": total_queries,
        "sql_success_rate": round(sql_success_rate, 2),
        "avg_latency_ms": int(avg_latency),
        "empty_result_rate": round(empty_result_rate, 2),
        "avg_satisfaction": round(avg_sat, 2),
        "satisfaction_count": sat_count
    }
