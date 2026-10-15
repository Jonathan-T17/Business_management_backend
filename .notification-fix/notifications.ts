import { safeInternalUrl } from "@/utils/internalUrl";
import type {
  Notification,
} from "@/types/notification";


export function notificationHref(
  notification: Notification
): string | null {
  if (notification.url) {
    const safe = safeInternalUrl(notification.url);
    if (safe) return safe;
  }

  const reference =
    notification.reference_id;

  if (!reference) {
    return null;
  }


  switch (
    notification.notification_type
  ) {
    case "WORKFLOW_ACTION":
      return /^\d+$/.test(reference) ? `/approvals/${reference}` : null;

    case "TASK_ASSIGNED":
    case "TASK_UPDATED":
    case "TASK_DELETED":
      return `/tasks/${reference}`;


    case "REPORT_CREATED":
    case "REPORT_SUBMITTED":
    case "REPORT_COMMENT":
    case "COMMENT_REPLY":
      return `/reports/${reference}`;


    case "PROJECT_CREATED":
    case "PROJECT_UPDATED":
    case "PROJECT_DELETED":
    case "MEMBERSHIP_CREATED":
    case "ROLE_CHANGED":
    case "OWNERSHIP_TRANSFERRED":
    case "PROJECT_INVITE":
      return `/projects/${reference}`;


    case "INVITATION":
      return "/users";


    case "AI_INSIGHT":
      return "/analytics";


    case "SECURITY":
      return "/settings";


    default:
      return null;
  }
}
