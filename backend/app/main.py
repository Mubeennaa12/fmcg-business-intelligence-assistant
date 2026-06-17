import csv
import io
import uuid
from datetime import datetime, date
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
import os
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd

from app.config import settings
from app.database import get_db, engine, Base
from app.models import ChatSession, ChatMessage, Product, Store, Sale, Inventory, EvaluationMetric
from app.data_generator import seed_database
from app.analytics import get_kpi_summary
from app.agent import agent
from app.evaluation import get_evaluation_summary, log_evaluation_metric
from app.report import generate_pdf_report

app = FastAPI(title=settings.PROJECT_NAME)

# Enable CORS for frontend local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify front-end domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to seed database if empty
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        # Seed
        seed_database(db)
    except Exception as e:
        print(f"Error seeding database on startup: {e}")
    finally:
        db.close()

# Pydantic Schemas
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class FeedbackRequest(BaseModel):
    satisfaction_score: int  # 1 (thumbs up) or 0 (thumbs down)

class ExportRequest(BaseModel):
    sql: str

# Endpoints

@app.post("/api/db/seed")
def force_seed_db(db: Session = Depends(get_db)):
    try:
        seed_database(db)
        return {"status": "success", "message": "Database seeded successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed database: {str(e)}")

@app.post("/api/chat")
def post_chat_message(req: ChatRequest, db: Session = Depends(get_db)):
    session_id = req.session_id
    
    # 1. Initialize session if not exists
    if not session_id:
        session_id = str(uuid.uuid4())
        # Generate a friendly title based on first query (limit size)
        title = req.message[:50] + "..." if len(req.message) > 50 else req.message
        db_session = ChatSession(session_id=session_id, title=title, created_at=datetime.utcnow())
        db.add(db_session)
        db.commit()
    else:
        db_session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not db_session:
            # Recreate session if missing in database
            db_session = ChatSession(session_id=session_id, title=req.message[:50], created_at=datetime.utcnow())
            db.add(db_session)
            db.commit()

    # 2. Save User Message
    user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=req.message,
        created_at=datetime.utcnow()
    )
    db.add(user_msg)
    db.commit()

    # 3. Execute AI Agent
    result = agent.run_query(req.message, db, session_id)
    
    # 4. Save Assistant Message
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=result.get("explanation", ""),
        sql_queries=result.get("sql", ""),
        query_results=json_dump_safe(result.get("data", [])),
        chart_type=result.get("chart_type", "text"),
        created_at=datetime.utcnow()
    )
    db.add(assistant_msg)
    db.commit()

    return {
        "session_id": session_id,
        "message_id": assistant_msg.id,
        "response": result.get("explanation", ""),
        "chart_type": result.get("chart_type", "text"),
        "sql": result.get("sql", ""),
        "data": result.get("data", []),
        "suggested_questions": result.get("suggested_questions", []),
        "is_ambiguous": result.get("is_ambiguous", False),
        "options": result.get("options", [])
    }

@app.get("/api/chat/sessions")
def get_chat_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
    return [{"session_id": s.session_id, "title": s.title, "created_at": s.created_at} for s in sessions]

@app.get("/api/chat/sessions/{session_id}/messages")
def get_session_messages(session_id: str, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    
    res = []
    for msg in messages:
        # Safely parse JSON results
        data_parsed = []
        if msg.query_results:
            try:
                import json
                data_parsed = json.loads(msg.query_results)
            except Exception:
                data_parsed = []
                
        res.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "sql": msg.sql_queries or "",
            "chart_type": msg.chart_type or "text",
            "data": data_parsed,
            "created_at": msg.created_at
        })
    return res

@app.post("/api/evaluation/feedback")
def submit_feedback(req: FeedbackRequest, db: Session = Depends(get_db)):
    # Update the latest evaluation record with the feedback score
    latest_eval = db.query(EvaluationMetric).order_by(EvaluationMetric.timestamp.desc()).first()
    if latest_eval:
        latest_eval.user_satisfaction = req.satisfaction_score
        db.commit()
        return {"status": "success", "message": "Feedback submitted successfully."}
    else:
        raise HTTPException(status_code=404, detail="No query evaluation metric found to score.")

@app.get("/api/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    # Convert whole sales/inventory tables to pandas dataframes to run analytics functions
    try:
        sales_df = pd.read_sql_table("sales", engine)
        inv_df = pd.read_sql_table("inventory", engine)
        summary = get_kpi_summary(sales_df, inv_df)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard summary: {str(e)}")

@app.get("/api/dashboard/charts")
def get_dashboard_charts(db: Session = Depends(get_db)):
    try:
        # 1. Weekly Revenue Trend
        weekly_res = db.execute(text("""
            SELECT week_start_date, SUM(revenue) as revenue, SUM(units_sold) as units 
            FROM sales 
            GROUP BY week_start_date 
            ORDER BY week_start_date
        """)).all()
        weekly_trend = [
            {"date": str(row[0]), "revenue": round(row[1], 2), "units": row[2]} for row in weekly_res
        ]
        
        # 2. Regional Sales Distribution
        region_res = db.execute(text("""
            SELECT region, SUM(revenue) as revenue, SUM(units_sold) as units 
            FROM sales 
            GROUP BY region 
            ORDER BY revenue DESC
        """)).all()
        regional_performance = [
            {"region": row[0], "revenue": round(row[1], 2), "units": row[2]} for row in region_res
        ]
        
        # 3. Category Distribution
        cat_res = db.execute(text("""
            SELECT p.category, SUM(s.revenue) as revenue, SUM(s.units_sold) as units 
            FROM sales s 
            JOIN products p ON s.product_id = p.product_id 
            GROUP BY p.category 
            ORDER BY revenue DESC
        """)).all()
        category_distribution = [
            {"category": row[0], "revenue": round(row[1], 2), "units": row[2]} for row in cat_res
        ]
        
        # 4. Top 10 Products Table
        top_prod_res = db.execute(text("""
            SELECT p.product_name, p.category, SUM(s.units_sold) as units, SUM(s.revenue) as revenue 
            FROM sales s 
            JOIN products p ON s.product_id = p.product_id 
            GROUP BY p.product_name, p.category 
            ORDER BY revenue DESC 
            LIMIT 10
        """)).all()
        top_products = [
            {"product_name": row[0], "category": row[1], "units": row[2], "revenue": round(row[3], 2)} 
            for row in top_prod_res
        ]
        
        return {
            "weekly_trend": weekly_trend,
            "regional_performance": regional_performance,
            "category_distribution": category_distribution,
            "top_products": top_products
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load charts: {str(e)}")

@app.get("/api/dashboard/evaluation")
def get_eval_metrics(db: Session = Depends(get_db)):
    return get_evaluation_summary(db)

@app.post("/api/export")
def export_csv(req: ExportRequest, db: Session = Depends(get_db)):
    sql = req.sql.strip()
    
    # Simple SQL injection prevention: only allow SELECT queries
    if not sql.lower().startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed for security.")
        
    try:
        res = db.execute(text(sql))
        keys = list(res.keys())
        rows = [dict(row._mapping) for row in res]
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            
        csv_data = output.getvalue()
        output.close()
        
        headers = {"Content-Disposition": 'attachment; filename="query_export.csv"'}
        return StreamingResponse(iter([csv_data]), media_type="text/csv", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL Execution error: {str(e)}")

@app.get("/api/report/pdf")
def get_pdf_report(db: Session = Depends(get_db)):
    try:
        pdf_buffer = generate_pdf_report(db)
        headers = {"Content-Disposition": 'attachment; filename="FMCG_Beverage_BI_Report.pdf"'}
        return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

# Helper to dump JSON safely (handling decimals, dates, etc.)
def json_dump_safe(data):
    import json
    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            return super().default(obj)
    return json.dumps(data, cls=CustomEncoder)

# Frontend SPA Static Assets and Routing Catch-all
static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")

@app.get("/{path_name:path}")
async def catch_all(path_name: str):
    # Skip routing for API calls (let them return 404 naturally if they don't match)
    if path_name.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
        
    # Check if the requested path is a file in static folder
    file_path = os.path.join(static_path, path_name)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
        
    # Check if it's a directory containing index.html (like root "/")
    index_path = os.path.join(static_path, path_name, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
        
    # Fallback to main index.html for client-side routing
    main_index = os.path.join(static_path, "index.html")
    if os.path.isfile(main_index):
        return FileResponse(main_index)
        
    return {"detail": "Frontend static assets not built. Run next build first."}

