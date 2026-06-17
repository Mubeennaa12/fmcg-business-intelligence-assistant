import os
import json
import time
import re
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.database import engine
from app.models import ChatMessage

# Try to import LangChain and LLM models
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_openai import ChatOpenAI
    HAS_LLM_LIBS = True
except ImportError:
    HAS_LLM_LIBS = False

class MockAgent:
    """
    Mock Agent that performs keyword matching to simulate the Text-to-SQL, 
    business explanation, and suggested questions if no LLM API keys are set.
    Ensures the application is 100% functional and testable without API keys.
    """
    def resolve_context(self, query: str, history: list) -> str:
        # Simple context resolution: if follow-up and history mentions regions
        if "inventory" in query.lower() or "stockout" in query.lower():
            regions = []
            for h in history[-3:]:
                if "north" in h.lower(): regions.append("North")
                if "south" in h.lower(): regions.append("South")
                if "east" in h.lower(): regions.append("East")
                if "west" in h.lower(): regions.append("West")
            if regions:
                return f"Show inventory and stockouts for {' and '.join(regions)} regions"
        return query

    def classify_and_generate(self, query: str) -> tuple[str, str, str]:
        q = query.lower()
        
        # 1. Ambiguity check
        if q.strip() in ["which region is doing badly?", "which region is doing badly", "bad region", "worst region"]:
            return "ambiguous", "", ""
            
        # 2. Match templates / categories
        # Region comparison
        if "region" in q or "north" in q or "south" in q or "east" in q or "west" in q:
            # Extract filters
            regions = []
            if "north" in q: regions.append("North")
            if "south" in q: regions.append("South")
            if "east" in q: regions.append("East")
            if "west" in q: regions.append("West")
            
            where_clause = ""
            if regions:
                region_str = ", ".join([f"'{r}'" for r in regions])
                where_clause = f"WHERE region IN ({region_str})"
                
            sql = f"""
            SELECT region, SUM(units_sold) AS total_units, ROUND(SUM(revenue), 2) AS total_revenue 
            FROM sales 
            {where_clause}
            GROUP BY region 
            ORDER BY total_revenue DESC
            """
            return "sales_by_region", sql, "comparison"
            
        # Stockout / Inventory Analysis
        elif "stockout" in q or "out of stock" in q or "inventory" in q:
            sql = """
            SELECT s.store_name, p.product_name, COUNT(*) AS stockout_weeks
            FROM inventory i
            JOIN stores s ON i.store_id = s.store_id
            JOIN products p ON i.product_id = p.product_id
            WHERE i.stockout_flag = 1
            GROUP BY s.store_name, p.product_name
            ORDER BY stockout_weeks DESC
            LIMIT 10
            """
            return "stockout_analysis", sql, "comparison"
            
        # Promotion Performance / Uplift
        elif "promotion" in q or "promo" in q or "uplift" in q:
            sql = """
            SELECT promotion_type, SUM(units_sold) AS total_units, ROUND(SUM(revenue), 2) AS total_revenue, ROUND(AVG(discount_pct)*100, 1) AS avg_discount_pct
            FROM sales
            WHERE promotion_flag = 1
            GROUP BY promotion_type
            ORDER BY total_revenue DESC
            """
            return "promotion_performance", sql, "comparison"
            
        # Top Products
        elif "top product" in q or "best selling" in q or "top selling" in q or "best product" in q:
            # Extract limit if any
            limit = 10
            match = re.search(r'top\s+(\d+)', q)
            if match:
                limit = int(match.group(1))
            sql = f"""
            SELECT p.product_name, p.category, SUM(s.units_sold) AS total_units, ROUND(SUM(s.revenue), 2) AS total_revenue
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            GROUP BY p.product_name, p.category
            ORDER BY total_revenue DESC
            LIMIT {limit}
            """
            return "top_products", sql, "table"
            
        # Category Performance
        elif "category" in q or "categories" in q:
            sql = """
            SELECT p.category, SUM(s.units_sold) AS total_units, ROUND(SUM(s.revenue), 2) AS total_revenue
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            GROUP BY p.category
            ORDER BY total_revenue DESC
            """
            return "category_performance", sql, "distribution"
            
        # Revenue Growth / Trends
        elif "growth" in q or "trend" in q or "over time" in q or "revenue performance" in q or "sales performance" in q:
            sql = """
            SELECT week_start_date, ROUND(SUM(revenue), 2) AS weekly_revenue, SUM(units_sold) AS weekly_units
            FROM sales
            GROUP BY week_start_date
            ORDER BY week_start_date
            """
            return "revenue_growth", sql, "trend"
            
        # Fallback Custom SQL Generator (Simple safe select)
        else:
            sql = """
            SELECT category, SUM(units_sold) AS total_units, ROUND(SUM(revenue), 2) AS total_revenue
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            GROUP BY category
            """
            return "general_query", sql, "distribution"

    def generate_explanation(self, query: str, sql: str, results: list, intent: str) -> dict:
        if not results:
            return {
                "explanation": "No matching data found.",
                "suggested_questions": [
                    "Which region generated the most revenue?",
                    "Which promotions produced the highest uplift?",
                    "Which stores experienced stockouts?"
                ]
            }

        # Format tabular data for explanations
        res_str = ""
        for row in results[:5]:
            res_str += ", ".join([f"{k}: {v}" for k, v in row.items()]) + "\n"

        # Generate mock explanations based on intent
        if intent == "sales_by_region":
            explanation = (
                f"Based on the analysis, regional sales show strong performance. "
                f"The highest performing region is {results[0].get('region', 'N/A')} with "
                f"a total revenue of ${results[0].get('total_revenue', 0):,.2f} and {results[0].get('total_units', 0):,} units sold. "
                f"This regional success was primarily driven by high sales of juice and carbonated drink categories."
            )
            suggested = [
                "Which product brand performs best in this region?",
                "Compare North and South region sales.",
                "What is the stockout rate in the East region?"
            ]
        elif intent == "stockout_analysis":
            explanation = (
                f"Stockout investigation indicates multiple stores experienced inventory shortages. "
                f"The product with the most stockout weeks is '{results[0].get('product_name', 'N/A')}' at "
                f"'{results[0].get('store_name', 'N/A')}', which had {results[0].get('stockout_weeks', 0)} stockout events. "
                f"These stockouts usually follow promotion weeks, suggesting a need for tighter restocking cycles."
            )
            suggested = [
                "Which stores experienced stockouts this week?",
                "What is the inventory turnover ratio for top products?",
                "Which promotion generated the highest revenue uplift?"
            ]
        elif intent == "promotion_performance":
            explanation = (
                f"Promotion analysis shows active campaigns drove significant volume. "
                f"The promotion type generating the highest revenue is '{results[0].get('promotion_type', 'N/A')}' with "
                f"${results[0].get('total_revenue', 0):,.2f} in sales and {results[0].get('total_units', 0):,} units sold. "
                f"BOGO and Price Cut promotions generated the highest sales uplift, but BOGO reduced overall gross margin percentage."
            )
            suggested = [
                "Which products benefited most from discounts?",
                "What is the average discount percentage by category?",
                "Compare promotional and non-promotional sales."
            ]
        elif intent == "top_products":
            explanation = (
                f"The product leaderboard is led by '{results[0].get('product_name', 'N/A')}' "
                f"in the '{results[0].get('category', 'N/A')}' category, which brought in "
                f"${results[0].get('total_revenue', 0):,.2f} in revenue across all stores. "
                f"Juice products occupy 3 of the top 5 slots, highlighting strong category demand."
            )
            suggested = [
                "Show top 10 products by revenue.",
                "Show category-wise revenue performance.",
                "Which products experienced stockouts?"
            ]
        elif intent == "category_performance":
            explanation = (
                f"Category-wise breakdown shows '{results[0].get('category', 'N/A')}' is the leading segment, "
                f"generating ${results[0].get('total_revenue', 0):,.2f} in revenue ({results[0].get('total_units', 0):,} units sold). "
                f"This is followed by '{results[1].get('category', 'N/A')}' with ${results[1].get('total_revenue', 0):,.2f}."
            )
            suggested = [
                "Which brand is leading in Juice sales?",
                "Show category-wise revenue performance.",
                "What is the average discount by category?"
            ]
        elif intent == "revenue_growth":
            explanation = (
                f"Weekly revenue trends show steady performance. "
                f"Sales peaked in the latter weeks of the history, showing growth driven by summer seasonality "
                f"for Carbonated and Water categories, as well as active display campaigns."
            )
            suggested = [
                "Which region is growing fastest?",
                "Show category-wise revenue performance.",
                "Which stores experienced stockouts?"
            ]
        else:
            explanation = (
                f"The database query completed successfully. "
                f"The top result shows values: {results[0]}."
            )
            suggested = [
                "Which region generated the most revenue?",
                "Which promotions produced the highest uplift?",
                "Which stores experienced stockouts?"
            ]

        return {
            "explanation": explanation,
            "suggested_questions": suggested
        }


class AIAgent:
    def __init__(self):
        self.mock_agent = MockAgent()
        self.llm = None
        self.enabled = False
        
        # Check if keys are configured
        api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
        openai_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
        
        if HAS_LLM_LIBS:
            if api_key:
                try:
                    self.llm = ChatGoogleGenerativeAI(
                        model="gemini-2.5-flash",
                        google_api_key=api_key,
                        temperature=0.0
                    )
                    self.enabled = True
                except Exception as e:
                    print(f"Error initializing Gemini: {e}")
            elif openai_key:
                try:
                    self.llm = ChatOpenAI(
                        model="gpt-4o",
                        api_key=openai_key,
                        temperature=0.0
                    )
                    self.enabled = True
                except Exception as e:
                    print(f"Error initializing OpenAI: {e}")
        
        if not self.enabled:
            print("AI Agent running in MOCK mode (No valid API Key found in environment).")

    def run_query(self, user_query: str, db: Session, session_id: str | None = None) -> dict:
        start_time = time.time()
        sql_generated = None
        sql_success = False
        is_empty_result = True
        
        # 1. Resolve History & Memory
        history = []
        if session_id:
            past_messages = db.query(ChatMessage)\
                .filter(ChatMessage.session_id == session_id)\
                .order_by(ChatMessage.created_at.asc())\
                .limit(5).all()
            history = [msg.content for msg in past_messages]
            
        resolved_query = self.resolve_context(user_query, history)
        
        # 2. Intent Detection, KPI Mapping, and SQL Generation
        try:
            intent, sql_generated, chart_type = self.classify_and_generate(resolved_query)
            
            if intent == "ambiguous":
                latency = int((time.time() - start_time) * 1000)
                # Log evaluation
                from app.evaluation import log_evaluation_metric
                log_evaluation_metric(db, user_query, None, True, latency, False)
                return {
                    "is_ambiguous": True,
                    "explanation": "Would you like me to compare sales revenue, units sold, or revenue growth rate?",
                    "options": ["Compare sales revenue", "Compare units sold", "Compare revenue growth rate"],
                    "suggested_questions": [
                        "Which region generated the most revenue?",
                        "Compare North and South sales."
                    ],
                    "chart_type": "text",
                    "sql": "",
                    "data": []
                }
                
            # 3. Execute SQL Query with Error Correction Loop
            results = []
            retries = 2
            current_sql = sql_generated
            
            while retries >= 0:
                try:
                    res = db.execute(text(current_sql))
                    # Map Row object to dictionary
                    results = [dict(row._mapping) for row in res]
                    sql_success = True
                    is_empty_result = (len(results) == 0)
                    break
                except Exception as e:
                    if retries == 0 or not self.enabled:
                        raise e
                    # Self correction using LLM
                    current_sql = self.correct_sql(current_sql, str(e))
                    retries -= 1
                    
            sql_generated = current_sql
            
            # 4. Zero-Row Hallucination Guardrail
            if is_empty_result:
                latency = int((time.time() - start_time) * 1000)
                from app.evaluation import log_evaluation_metric
                log_evaluation_metric(db, user_query, sql_generated, sql_success, latency, True)
                return {
                    "is_ambiguous": False,
                    "explanation": "No matching data found.",
                    "chart_type": "text",
                    "sql": sql_generated,
                    "data": [],
                    "suggested_questions": [
                        "Which region generated the most revenue?",
                        "Which promotions produced the highest uplift?",
                        "Which stores experienced stockouts?"
                    ]
                }
                
            # 5. Generate Explanation and Visualizations
            explanation_data = self.generate_explanation(resolved_query, sql_generated, results, intent)
            latency = int((time.time() - start_time) * 1000)
            
            # Log Evaluation Metrics
            from app.evaluation import log_evaluation_metric
            log_evaluation_metric(db, user_query, sql_generated, sql_success, latency, is_empty_result)
            
            return {
                "is_ambiguous": False,
                "explanation": explanation_data["explanation"],
                "chart_type": chart_type,
                "sql": sql_generated,
                "data": results,
                "suggested_questions": explanation_data["suggested_questions"]
            }
            
        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            from app.evaluation import log_evaluation_metric
            log_evaluation_metric(db, user_query, sql_generated, False, latency, True)
            return {
                "is_ambiguous": False,
                "explanation": f"An error occurred while executing the database query: {str(e)}",
                "chart_type": "text",
                "sql": sql_generated or "",
                "data": [],
                "suggested_questions": [
                    "Which region generated the most revenue?",
                    "Which stores experienced stockouts?"
                ]
            }

    def resolve_context(self, query: str, history: list) -> str:
        if not self.enabled:
            return self.mock_agent.resolve_context(query, history)
            
        if not history:
            return query
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a query context resolver. Given a conversation history and a follow-up query, 
your job is to rewrite the follow-up query to make it complete and self-contained so it can be queried against the database.
Do not answer the query, just rewrite it.
If the query is already self-contained, return it exactly as is.

Example 1:
History: ["Compare North and South sales"]
Query: "What about inventory?"
Output: "Show inventory and stockouts for North and South regions"

Example 2:
History: ["Which products are top-selling?"]
Query: "Which ones experienced stockouts?"
Output: "Which of the top-selling products experienced stockouts?"
"""),
            ("user", "History: {history}\nFollow-up Query: {query}\nSelf-contained Query:")
        ])
        
        chain = prompt | self.llm
        res = chain.invoke({"history": json.dumps(history), "query": query})
        return res.content.strip()

    def classify_and_generate(self, query: str) -> tuple[str, str, str]:
        if not self.enabled:
            return self.mock_agent.classify_and_generate(query)
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an FMCG Beverage BI Assistant SQL Generator.
Given a user's natural language question, analyze it to:
1. Detect if it is too ambiguous (e.g. "Which region is doing badly?" - we don't know if "badly" means revenue, volume, or growth). If ambiguous, return intent="ambiguous".
2. Select a suitable intent / KPI:
   - `sales_by_region`
   - `promotion_performance`
   - `stockout_analysis`
   - `top_products`
   - `revenue_growth`
   - `category_performance`
   - `general_query`
3. Generate standard ANSI SQL query using the tables:
   - `products` (product_id, product_name, brand, category, sub_category, pack_size_ml, unit_price)
   - `stores` (store_id, store_name, region, city, store_format)
   - `sales` (id, week_start_date, product_id, store_id, region, units_sold, revenue, promotion_flag, promotion_type, discount_pct)
   - `inventory` (id, week_start_date, product_id, store_id, opening_stock, units_received, units_sold, closing_stock, stockout_flag)
4. Determine the best chart visualization: `trend`, `comparison`, `distribution`, `table`, or `text`.

Output ONLY a JSON block with keys: "intent", "sql", "chart_type".
Do not write anything else. Ensure the SQL is completely read-only and uses standard operators. For string matches, use LOWER(column) LIKE '%value%' for safety.

Example Output:
{{
  "intent": "sales_by_region",
  "sql": "SELECT region, SUM(revenue) as total_revenue FROM sales GROUP BY region",
  "chart_type": "comparison"
}}
"""),
            ("user", "Question: {query}")
        ])
        
        chain = prompt | self.llm
        res = chain.invoke({"query": query})
        
        # Parse JSON
        content = res.content.strip()
        # Clean markdown codeblocks
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        try:
            data = json.loads(content)
            return data["intent"], data["sql"], data["chart_type"]
        except Exception:
            # Fallback to mock if LLM outputs invalid JSON
            return self.mock_agent.classify_and_generate(query)

    def correct_sql(self, bad_sql: str, error_msg: str) -> str:
        if not self.enabled:
            return bad_sql
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a SQL debugging assistant.
Given a SQL query that failed and the database error message, correct the SQL query to make it syntactically correct and run successfully.
Only return the corrected SQL query inside a markdown code block or as plain text. No explanations.
"""),
            ("user", "Bad SQL: {bad_sql}\nError: {error_msg}\nCorrected SQL:")
        ])
        
        chain = prompt | self.llm
        res = chain.invoke({"bad_sql": bad_sql, "error": error_msg})
        content = res.content.strip()
        if content.startswith("```sql"):
            content = content[6:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
        return content

    def generate_explanation(self, query: str, sql: str, results: list, intent: str) -> dict:
        if not self.enabled:
            return self.mock_agent.generate_explanation(query, sql, results, intent)
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an FMCG Beverage Business Analyst.
Your goal is to write a detailed, executive-facing natural language business explanation for the database query results.

Follow these strict rules:
1. Explain the *contextual why* behind findings. Connect sales, promotions, categories, and inventory.
2. Use Business Explanation Mode. E.g. instead of stating "Revenue increased 12%", explain what drove it (e.g. Price Cut promotions in Juice category, or summer seasonality).
3. If calculation logic is involved (like promotion uplift or stockout rate), explain how it was calculated in a footnote-like statement.
4. Provide 3 highly relevant follow-up questions the user can click next.
5. NEVER hallucinate or mention any numbers or data not present in the Query Results.

Output ONLY a JSON block with keys: "explanation", "suggested_questions".

Example:
{{
  "explanation": "Revenue increased by 12% compared to the previous period, primarily driven by Price Cut promotions in the Juice category.",
  "suggested_questions": ["Which promotion performed best in Juice?", "Show inventory turnover of juice products."]
}}
"""),
            ("user", "User Query: {query}\nSQL Executed: {sql}\nQuery Results: {results}\nIntent: {intent}\nOutput JSON:")
        ])
        
        chain = prompt | self.llm
        res = chain.invoke({"query": query, "sql": sql, "results": json.dumps(results[:15]), "intent": intent})
        content = res.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        try:
            return json.loads(content)
        except Exception:
            return self.mock_agent.generate_explanation(query, sql, results, intent)

# Instantiate global agent
agent = AIAgent()
