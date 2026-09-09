import inspect

def test_workflow_runtime_has_locked_approve_reject_return_contract():
    from workflows.runtime_service import WorkflowRuntimeService
    for method_name in ('approve', 'reject', 'return_for_changes'):
        assert hasattr(WorkflowRuntimeService, method_name)
        source = inspect.getsource(getattr(WorkflowRuntimeService, method_name))
        assert 'atomic' in source or 'select_for_update' in source
