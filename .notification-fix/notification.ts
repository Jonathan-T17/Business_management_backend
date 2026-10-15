export type NotificationType =
  | "WORKFLOW_ACTION"
  | "REQUEST_UPDATE"
  | "TASK_ASSIGNED"
  | "TASK_UPDATED"
  | "TASK_DELETED"
  | "REPORT_CREATED"
  | "REPORT_SUBMITTED"
  | "REPORT_COMMENT"
  | "COMMENT_REPLY"
  | "PROJECT_CREATED"
  | "PROJECT_UPDATED"
  | "PROJECT_DELETED"
  | "PROJECT_INVITE"
  | "MEMBERSHIP_CREATED"
  | "ROLE_CHANGED"
  | "OWNERSHIP_TRANSFERRED"
  | "INVITATION"
  | "SECURITY"
  | "SYSTEM"
  | "AI_INSIGHT";

export interface Notification {
  id: string;
  recipient: string;
  company: number;
  branch: number | null;
  notification_type: NotificationType;
  title: string;
  message: string;
  preview?: string | null;
  sensitive?: boolean;
  reference_id: string | null;
  url: string | null;
  is_read: boolean;
  allowed_actions?: Array<"OPEN" | "MARK_READ" | "MARK_UNREAD" | "DELETE">;
  created_at: string;
}

export interface UnreadCount { count: number; }
