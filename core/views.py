from django.db.models import Count

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.roles import Roles
from core.tenant import TenantService
from notifications.models import Notification
from activity.models import ActivityLog
from companies.models import Branch
from organizations.models import Department, Team
from users.models import User


class DashboardView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		user = request.user
		role = user.role

		projects = TenantService.projects(user)
		tasks = TenantService.tasks(user)
		reports = TenantService.reports(user)
		notifications = TenantService.notifications(user)
		activity = TenantService.activity(user)
		company_filter = {}
		if role != Roles.SUPERUSER:
			company_filter = {"company_id": user.company_id}

		organization_counts = {
			"employees": User.objects.filter(
				**company_filter,
				is_deleted=False,
			).exclude(role=Roles.SUPERUSER).count(),
			"branches": Branch.objects.filter(**company_filter).count(),
			"departments": Department.objects.filter(**company_filter).count(),
			"teams": Team.objects.filter(**company_filter).count(),
			"activity": activity.count(),
		}

		dashboard = {
			Roles.SUPERUSER: "platform",
			Roles.ADMIN: "company",
			Roles.MANAGER: "manager",
			Roles.EMPLOYEE: "employee",
			Roles.INDIVIDUAL: "individual",
		}.get(role, "individual")

		task_counts = tasks.values("status").annotate(total=Count("id"))
		status_counts = {
			item["status"]: item["total"]
			for item in task_counts
		}

		recent_tasks = [
			{
				"id": task.id,
				"title": task.title,
				"status": task.status,
				"project_id": task.project_id,
				"due_date": task.due_date,
				"is_overdue": task.is_overdue(),
			}
			for task in tasks.select_related("project")[:10]
		]

		recent_projects = [
			{
				"id": project.id,
				"name": project.name,
				"description": project.description,
				"is_active": project.is_active,
			}
			for project in projects[:10]
		]

		company = getattr(user, "company", None)

		return Response({
			"role": role,
			"dashboard": dashboard,
			"user": {
				"id": str(user.id),
				"email": user.email,
				"full_name": user.full_name,
				"role": role,
				"company_id": user.company_id,
				"branch_id": user.branch_id,
			},
			"company": (
				{
					"id": company.id,
					"name": company.name,
					"slug": company.slug,
				}
				if company
				else None
			),
			"summary": {
				**organization_counts,
				"projects": projects.count(),
				"tasks": tasks.count(),
				"reports": reports.count(),
				"unread_notifications": notifications.filter(
					is_read=False
				).count(),
				"tasks_by_status": status_counts,
			},
			"recent_projects": recent_projects,
			"recent_tasks": recent_tasks,
			"recent_activity": [
				{
					"id": item.id,
					"action": item.action,
					"user_id": item.user_id,
					"project_id": item.project_id,
					"task_id": item.task_id,
					"metadata": item.metadata,
					"created_at": item.created_at,
				}
				for item in activity.select_related(
					"user",
					"project",
					"task",
				)[:20]
			],
			"endpoints": {
				"profile": "/api/users/me/",
				"notifications": "/api/notifications/",
				"projects": "/api/projects/",
				"tasks": "/api/tasks/",
				"reports": "/api/reports/",
			},
		})
