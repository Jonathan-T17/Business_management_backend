"""Migration guidance:
ConversationMember: add role MEMBER/MODERATOR, can_manage_members, left_at.
Message: remove attachment_url; use GenericRelation documents.Attachment; add deleted_by/edit_version if missing.
Platform identities never gain implicit tenant chat access. Company ADMIN is not an implicit DM moderator.
"""
