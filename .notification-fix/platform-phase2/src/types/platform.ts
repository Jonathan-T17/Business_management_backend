export interface PlatformDashboard {
  companies: {
    total: number;
    active: number;
    new_this_month: number;
  };

  users: {
    total: number;
    active: number;
    new_this_month: number;
  };

  projects: {
    total: number;
    active: number;
  };

  tasks: {
    total: number;
    active: number;
    completed: number;
  };

  reports: {
    total: number;
    last_24h: number;
  };

  security: {
    active_sessions: number;
    failed_logins_24h: number;
    locked_records: number;
    critical_events_24h: number;
  };

  subscriptions: {
    active: number;
    expired: number;
    expiring_soon: number;
  };

  recent_audit_events: PlatformAuditLog[];
  recent_companies: PlatformCompany[];

  system_health: PlatformHealth;
}


export type PlatformCompanyAction = "DEACTIVATE" | "REACTIVATE" | "VIEW_SECURITY" | "VIEW_SUBSCRIPTION";
export type PlatformUserAction = "DEACTIVATE" | "REACTIVATE" | "REQUIRE_PASSWORD_RESET" | "TERMINATE_SESSIONS";
export type PlatformSessionAction = "TERMINATE";
export type PlatformFailedLoginAction = "UNLOCK";

export interface PlatformCompany {
  id: number;
  name: string;
  slug: string;
  email: string;
  phone: string;
  website: string;
  address: string;
  is_active: boolean;

  users_count: number;
  branches_count: number;
  projects_count: number;

  subscription_plan: string | null;
  subscription_active: boolean;

  created_at: string;
  updated_at: string;
  allowed_actions?: PlatformCompanyAction[];
}


export interface PlatformUser {
  id: string;
  email: string;
  full_name: string;
  role: string;

  company: number | null;
  company_name: string | null;

  branch: number | null;
  branch_name: string | null;

  is_active: boolean;
  email_verified: boolean;
  is_deleted: boolean;
  mfa_enabled: boolean;

  last_login_ip: string | null;
  last_activity: string | null;

  date_joined: string;
  allowed_actions?: PlatformUserAction[];
}


export interface PlatformActiveSession {
  id: number;

  user: string;
  user_email: string;

  company: number | null;
  company_name: string | null;

  branch: number | null;

  ip_address: string;
  browser: string;
  operating_system: string;
  device: string;

  last_activity: string;
  expires_at: string | null;
  terminated_at: string | null;

  is_active: boolean;
  allowed_actions?: PlatformSessionAction[];
}


export interface PlatformLoginHistory {
  id: number;

  user: string;
  user_email: string;

  company: number | null;
  company_name: string | null;

  branch: number | null;

  ip_address: string;
  browser: string;
  operating_system: string;
  device: string;
  location: string;

  successful: boolean;
  failure_reason: string;

  created_at: string;
}


export interface PlatformFailedLogin {
  id: number;
  email: string;

  company: number | null;
  company_name: string | null;

  ip_address: string;

  attempts: number;
  reason: string;
  locked_until: string | null;
  locked_by_system: boolean;
  last_attempt_at: string;
  allowed_actions?: PlatformFailedLoginAction[];
}


export interface PlatformAuditLog {
  id: number;

  user: string | null;
  user_email: string | null;

  company: number | null;
  company_name: string | null;

  branch: number | null;

  action: string;
  severity: string;
  actor_type: string;

  object_type: string;
  object_id: number | null;

  description: string;

  ip_address: string | null;
  user_agent: string;

  status: string;

  created_at: string;
}


export interface PlatformSubscription {
  is_valid: boolean;
  id: number;

  company: number;
  company_name: string;

  plan: number;
  plan_name: string;

  max_users: number;
  users_used: number;

  max_projects: number;
  projects_used: number;

  is_active: boolean;

  started_at: string;
  expires_at: string | null;
  renewed_at: string | null;
}


export interface PlatformActivity {
  id: number;
  action: string;
  summary?: string | null;
  actor_email?: string | null;
  company_name?: string | null;
  created_at: string;
}

export interface PlatformHealth {
  services?: Record<string, {status: string; detail?: string; last_run?: string}>;
  status: string;

  database: {
    status: string;
  };

  cache: {
    status: string;
  };

  email: {
    status: string;
    backend: string;
  };

  timestamp: string;
}