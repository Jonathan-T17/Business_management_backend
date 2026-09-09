import inspect

def test_business_services_do_not_use_count_plus_one_numbering():
    offenders = []
    candidates = [('reports.services','ReportService'),('requests_app.services','BusinessRequestService')]
    for module_name, cls_name in candidates:
        try:
            module = __import__(module_name, fromlist=[cls_name]); cls = getattr(module, cls_name)
        except (ImportError, AttributeError):
            continue
        if '.count()+1' in inspect.getsource(cls).replace(' ',''):
            offenders.append(f'{module_name}.{cls_name}')
    assert not offenders, 'Race-prone count()+1 numbering: ' + ', '.join(offenders)
