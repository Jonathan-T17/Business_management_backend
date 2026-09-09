# SmartBiz Phase 4 — Projects, Tasks & Comments

This package is an integration patch for the existing backend. Apply after Phases 1–3.

## Required model migrations

### ProjectMembership
Add a conditional database constraint enforcing one OWNER per project. Keep the existing unique `(project, user)` constraint.

### Project
Keep historical projects. `is_active=False` is archive state. Do not expose generic DELETE for projects with any business history.

### Task
`company`, `created_by`, `project`, and `is_active` must be read-only through generic serializers after creation. Status changes must use `TaskService.change_status()` rather than generic PATCH. Project moves require a future dedicated move action and must not be accepted through PATCH.

### Comment
Add:
- `edited_at = DateTimeField(null=True, blank=True)`
- `is_deleted = BooleanField(default=False)`
- `deleted_at = DateTimeField(null=True, blank=True)`
- `deleted_by = ForeignKey(User, null=True, blank=True, SET_NULL, related_name='+')`

Do not hard-delete normal comments. Retain moderation/audit evidence.

## ViewSet contract

Projects:
- queryset: `ProjectAccess.visible_queryset(request.user)`
- create: capability `MANAGE_PROJECTS` + entitlement check + `ProjectService.create_project`
- update: `ProjectService.update_project`
- archive/restore: explicit actions
- transfer ownership: explicit action; reason recommended
- membership changes: service only
- platform superusers do not use tenant project endpoints

Tasks:
- queryset: tasks whose project is in `ProjectAccess.visible_queryset(user)`
- create: `TaskService.create_task`
- PATCH cannot change project/status/is_active/company/created_by
- status: explicit `change-status` action
- complete: `TaskService.complete`
- deactivate/restore: explicit service actions
- managers/owners manage; assignees may work/change status; contributors may create when project policy permits

Comments:
- queryset follows project visibility
- creation through `CommentService.create`
- ordinary edit is author-only
- delete is soft-delete
- moderation requires an explicit moderation capability; Company Admin is not automatically comment moderator

## Notification contract

Do not notify every project member for every task mutation. Target:
- newly assigned users
- removed assignees when useful
- task creator
- project owner/manager/watchers for important state changes

Before delivery, ensure each recipient still has source-object visibility. Notification bodies must not contain private comment/task content unnecessarily.

## Employee replacement integration

Employee replacement may reassign open tasks and project memberships, but must never rewrite `created_by`, TaskActivity authorship, comment authorship, or other historical authorship.

## Attachments

Attachment authorization inherits its parent Project/Task/Comment visibility and action state. An attachment must never widen parent visibility.

## Bulk operations

`BulkTaskService` must resolve IDs through the same task-visible queryset and call `TaskService.change_status()` under row locks. Company ID filtering alone is insufficient authorization.

## Test matrix

Required tests include:
- cross-company UUID returns 404
- platform identity receives no tenant project/task/comment data
- Company Admin without project membership cannot silently read project content
- owner/manager/member/viewer action differences
- one-owner constraint and concurrent ownership transfer
- archived project cannot accept new tasks
- assignee can change status but cannot reassign/manage project
- non-assignee member cannot complete a task unless project manager/owner
- inactive/terminated user cannot be assigned
- assignee must be project member
- task project cannot change through PATCH
- task is_active cannot change through PATCH
- author-only comment editing
- moderation capability behavior
- soft deletion preservation
- notification recipient visibility
- employee replacement preserves history
