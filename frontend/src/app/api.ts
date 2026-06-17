const API_BASE_URL = typeof window !== "undefined"
  ? `${window.location.origin}/api`
  : "http://localhost:8000/api";

export interface KPISummary {
  total_revenue: number;
  total_units_sold: number;
  active_promotions_pct: number;
  stockout_rate: number;
}

export interface ChartData {
  weekly_trend: Array<{ date: string; revenue: number; units: number }>;
  regional_performance: Array<{ region: string; revenue: number; units: number }>;
  category_distribution: Array<{ category: string; revenue: number; units: number }>;
  top_products: Array<{ product_name: string; category: string; units: number; revenue: number }>;
}

export interface EvalSummary {
  total_queries: number;
  sql_success_rate: number;
  avg_latency_ms: number;
  empty_result_rate: number;
  avg_satisfaction: number;
  satisfaction_count: number;
}

export interface ChatSession {
  session_id: string;
  title: string;
  created_at: string;
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant";
  content: string;
  sql?: string;
  chart_type?: string;
  data?: Record<string, unknown>[];
  created_at?: string;
  suggested_questions?: string[];
  is_ambiguous?: boolean;
  options?: string[];
}

export const api = {
  async getDashboardSummary(): Promise<KPISummary> {
    const res = await fetch(`${API_BASE_URL}/dashboard/summary`);
    if (!res.ok) throw new Error("Failed to load dashboard summary");
    return res.json();
  },

  async getDashboardCharts(): Promise<ChartData> {
    const res = await fetch(`${API_BASE_URL}/dashboard/charts`);
    if (!res.ok) throw new Error("Failed to load chart data");
    return res.json();
  },

  async getEvalMetrics(): Promise<EvalSummary> {
    const res = await fetch(`${API_BASE_URL}/dashboard/evaluation`);
    if (!res.ok) throw new Error("Failed to load evaluation metrics");
    return res.json();
  },

  async getSessions(): Promise<ChatSession[]> {
    const res = await fetch(`${API_BASE_URL}/chat/sessions`);
    if (!res.ok) throw new Error("Failed to load chat sessions");
    return res.json();
  },

  async getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
    const res = await fetch(`${API_BASE_URL}/chat/sessions/${sessionId}/messages`);
    if (!res.ok) throw new Error("Failed to load chat messages");
    return res.json();
  },

  async sendChatMessage(
    message: string,
    sessionId: string | null = null
  ): Promise<{
    session_id: string;
    message_id: number;
    response: string;
    chart_type: string;
    sql: string;
    data: Record<string, unknown>[];
    suggested_questions: string[];
    is_ambiguous: boolean;
    options: string[];
  }> {
    const res = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    if (!res.ok) throw new Error("Failed to send chat message");
    return res.json();
  },

  async submitFeedback(score: number): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/evaluation/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ satisfaction_score: score }),
    });
    if (!res.ok) throw new Error("Failed to submit feedback");
  },

  async forceSeedDb(): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/db/seed`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to seed database");
  },

  async exportCSV(sql: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sql }),
    });
    if (!res.ok) throw new Error("Failed to export CSV");
    
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `FMCG_export_${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },

  getPDFReportUrl(): string {
    return `${API_BASE_URL}/report/pdf`;
  }
};
