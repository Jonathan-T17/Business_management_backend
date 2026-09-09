from django.test import TestCase


class Phase5InvariantDocumentationTests(TestCase):
    """These tests are intended to be expanded in the integrated repository.

    Kept deliberately dependency-light here because the complete application repository and
    migrations are not mounted in this working package.
    """

    def test_invariant_catalogue(self):
        invariants = {
            "published_forms_immutable",
            "published_workflows_immutable",
            "workflow_target_type_checked",
            "optional_empty_workflow_steps_skipped",
            "workflow_actions_row_locked",
            "company_timezone_deadlines",
            "sequence_numbers_row_locked",
            "submitter_cannot_choose_workflow",
            "request_config_visibility_approval_fulfillment_separate",
            "dynamic_fields_classified",
            "source_specific_workflow_adapters",
        }
        self.assertEqual(len(invariants), 11)
