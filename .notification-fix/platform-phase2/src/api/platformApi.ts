import { platformClient } from "./client";
import { extractResults } from "@/utils/api";

import type {
  PlatformDashboard,
  PlatformCompany,
  PlatformUser,
  PlatformActiveSession,
  PlatformLoginHistory,
  PlatformFailedLogin,
  PlatformAuditLog,
  PlatformSubscription,
  PlatformActivity,
  PlatformHealth,
} from "@/types/platform";

export interface PlatformSettings {
  editable: false;
  settings: { access_token_minutes: number; refresh_token_days: number; frontend_url: string; email_configured: boolean };
  message: string;
}

export interface PlatformPlan {
  max_branches?: number;
  issues?: string[];
  id: number;
  name: string;
  description?: string | null;
  max_users?: number | null;
  max_projects?: number | null;
  is_active?: boolean;
}


export async function getPlatformDashboard(): Promise<PlatformDashboard> {
  const response = await platformClient.get("dashboard/");
  return response.data;
}


export async function getPlatformCompanies(
  params?: {
    search?: string;
    status?: string;
  }
): Promise<PlatformCompany[]> {
  const response = await platformClient.get(
    "companies/",
    { params }
  );

  return extractResults<PlatformCompany>(
    response.data
  );
}


export async function getPlatformCompany(
  id: number
): Promise<PlatformCompany> {
  const response = await platformClient.get(
    `companies/${id}/`
  );

  return response.data;
}


export async function activatePlatformCompany(
  id: number,
  reason: string
) {
  const response = await platformClient.post(
    `companies/${id}/reactivate/`,
    { reason }
  );
  return response.data;
}


export async function deactivatePlatformCompany(
  id: number,
  reason: string
) {
  const response = await platformClient.post(
    `companies/${id}/deactivate/`,
    { reason }
  );

  return response.data;
}


export async function getPlatformUsers(
  params?: {
    company?: number;
    role?: string;
    search?: string;
  }
): Promise<PlatformUser[]> {
  const response = await platformClient.get(
    "users/",
    { params }
  );

  return extractResults<PlatformUser>(
    response.data
  );
}


export async function terminateUserSessions(
  id: string,
  reason: string
) {
  const response = await platformClient.post(
    `users/${id}/terminate-sessions/`,
    { reason }
  );

  return response.data;
}


export async function getPlatformSessions(
  params?: {
    active?: boolean;
    company?: number;
  }
): Promise<PlatformActiveSession[]> {
  const response = await platformClient.get(
    "security/sessions/",
    {
      params: {
        ...(params?.active !== undefined
          ? {
              active: String(params.active),
            }
          : {}),
        ...(params?.company
          ? {
              company: params.company,
            }
          : {}),
      },
    }
  );

  return extractResults<PlatformActiveSession>(
    response.data
  );
}


export async function terminatePlatformSession(
  id: number,
  reason: string
) {
  const response = await platformClient.post(
    `security/sessions/${id}/terminate/`,
    { reason }
  );

  return response.data;
}


export async function getPlatformLoginHistory(
  params?: {
    successful?: boolean;
    company?: number;
  }
): Promise<PlatformLoginHistory[]> {
  const response = await platformClient.get(
    "security/login-history/",
    {
      params: {
        ...(params?.successful !== undefined
          ? {
              successful: String(
                params.successful
              ),
            }
          : {}),
        ...(params?.company
          ? {
              company: params.company,
            }
          : {}),
      },
    }
  );

  return extractResults<PlatformLoginHistory>(
    response.data
  );
}


export async function getPlatformFailedLogins(): Promise<
  PlatformFailedLogin[]
> {
  const response = await platformClient.get(
    "security/failed-logins/"
  );

  return extractResults<PlatformFailedLogin>(
    response.data
  );
}


export async function unlockFailedLogin(
  id: number,
  reason: string
) {
  const response = await platformClient.post(
    `security/failed-logins/${id}/unlock/`,
    { reason }
  );

  return response.data;
}


export async function getPlatformAuditLogs(
  params?: {
    company?: number;
    user?: string;
    action?: string;
    severity?: string;
    status?: string;
    object_type?: string;
  }
): Promise<PlatformAuditLog[]> {
  const response = await platformClient.get(
    "audit/",
    { params }
  );

  return extractResults<PlatformAuditLog>(
    response.data
  );
}


export async function getPlatformSubscriptionPage(page: number, search = "") {
  const response = await platformClient.get<import("@/utils/api").PaginatedResponse<PlatformSubscription>>("subscriptions/", { params: { page, search } });
  return response.data;
}

export async function getPlatformSubscriptions(): Promise<
  PlatformSubscription[]
> {
  const response = await platformClient.get(
    "subscriptions/"
  );

  return extractResults<PlatformSubscription>(
    response.data
  );
}


export async function changePlatformPlan(
  id: number,
  planId: number,
  reason: string
) {
  const response = await platformClient.post(
    `subscriptions/${id}/change-plan/`,
    {
      plan_id: planId,
      reason,
    }
  );

  return response.data;
}


export async function getPlatformActivity(): Promise<
  PlatformActivity[]
> {
  const response = await platformClient.get(
    "activity/"
  );

  return extractResults<PlatformActivity>(
    response.data
  );
}


export async function getPlatformHealth(): Promise<
  PlatformHealth
> {
  const response = await platformClient.get(
    "health/"
  );

  return response.data;
}

export async function getPlatformPlans(subscriptionId?: number): Promise<PlatformPlan[]> {
  const response = await platformClient.get(subscriptionId ? `subscriptions/${subscriptionId}/plan-options/` : "plans/");
  return extractResults<PlatformPlan>(response.data);
}

export async function getPlatformSettings(): Promise<PlatformSettings> {
  const response = await platformClient.get("settings/");
  return response.data;
}

export const platformApi = {
  async dashboard(): Promise<PlatformDashboard> { return (await platformClient.get("dashboard/")).data; },
  async companies(params: Record<string, unknown> = {}): Promise<PlatformCompany[]> { return extractResults<PlatformCompany>((await platformClient.get("companies/", { params })).data); },
  async company(id: string): Promise<PlatformCompany> { return (await platformClient.get(`companies/${id}/`)).data; },
  async deactivateCompany(id: string, reason: string) { return (await platformClient.post(`companies/${id}/deactivate/`, { reason })).data; },
  async reactivateCompany(id: string, reason: string) { return (await platformClient.post(`companies/${id}/reactivate/`, { reason })).data; },
  async users(params: Record<string, unknown> = {}): Promise<PlatformUser[]> { return extractResults<PlatformUser>((await platformClient.get("users/", { params })).data); },
  async user(id: string): Promise<PlatformUser> { return (await platformClient.get(`users/${id}/`)).data; },
  async deactivateUser(id: string, reason: string) { return (await platformClient.post(`users/${id}/deactivate/`, { reason })).data; },
  async reactivateUser(id: string, reason: string) { return (await platformClient.post(`users/${id}/reactivate/`, { reason })).data; },
  async requirePasswordReset(id: string, reason: string) { return (await platformClient.post(`users/${id}/require-password-reset/`, { reason })).data; },
  async sessions(params: Record<string, unknown> = {}): Promise<PlatformActiveSession[]> { return extractResults<PlatformActiveSession>((await platformClient.get("security/sessions/", { params })).data); },
  async terminateSession(id: string, reason: string) { return (await platformClient.post(`security/sessions/${id}/terminate/`, { reason })).data; },
  async auditLogs(params: Record<string, unknown> = {}): Promise<PlatformAuditLog[]> { return extractResults<PlatformAuditLog>((await platformClient.get("audit/", { params })).data); },
  async health(): Promise<PlatformHealth> { return (await platformClient.get("health/")).data; },
};
export async function getPlatformSecuritySummary() {
  const { data } = await platformClient.get<{security: PlatformDashboard["security"]; open_incidents: number; authentication: string}>("security/summary/");
  return data;
}
