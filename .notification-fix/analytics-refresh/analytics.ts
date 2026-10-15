export type SnapshotType =
  | "company"
  | "branch"
  | "project";

export type AIInsightType =
  | "COMPANY_SUMMARY"
  | "PROJECT_SUMMARY"
  | "WORKLOAD_ALERT"
  | "RISK_ALERT";


export interface AnalyticsSnapshot {
  id: number;

  company: number;
  branch: number | null;
  project: number | null;

  snapshot_type: SnapshotType;

  total_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;

  collaboration_score: number;
  workload_balance_score: number;

  ai_summary: string;

  generated_at: string;
}


export interface AIInsight {
  id: number;

  company: number;
  project: number | null;

  insight_type: AIInsightType;

  title: string;
  summary: string;

  generated_at: string;
}


export interface CompanyAnalyticsResponse {
  snapshots: AnalyticsSnapshot[];
  insights: AIInsight[];
}


export interface AnalyticsRecord {
  id: number;

  company: number;

  level:
    | "COMPANY"
    | "PROJECT"
    | "USER";

  reference_id: number;

  summary: string;

  generated_at: string;
}

export interface DashboardMetric {
  key: string;
  label: string;
  value: number | string;
  change?: number | null;
  period?: string;
}

export interface AnalyticsOverview {
  submissions?: Record<string, number>;
  submission_trend?: TrendPoint[];
  branch_activity?: { branch_id: number | null; name: string; total: number; approved: number; awaiting_review: number; returned: number; other: number }[];
  review_age?: { label: string; value: number }[];
  metrics: DashboardMetric[];
  tasks?: { total: number; todo: number; in_progress: number; done: number; overdue: number };
  projects?: { active: number; completed: number; on_hold: number };
  reporting?: { expected: number; submitted: number; late: number; missed: number; compliance_percentage: number };
  requests?: { submitted: number; under_review: number; approved: number; rejected: number; fulfilled: number };
}

export interface TrendPoint { date: string; value: number; }

export interface ScopedAIInsight {
  id: string;
  insight_type: string;
  title: string;
  summary: string;
  severity?: "INFO" | "WARNING" | "CRITICAL";
  confidence?: number | null;
  generated_at: string;
  related_module?: string | null;
  related_object_id?: string | null;
}