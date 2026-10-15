# Product-owned starter designs contain no tenant data or assignments.
STARTERS = [
    {'code':'collection-record','name':'Goods or materials collection','category':'COLLECTION','allow_drafts':True,'fields':[
        {'key':'collection_date','label':'Collection date','field_type':'DATE','required':True,'classification':'NORMAL'},
        {'key':'item','label':'Goods or material collected','field_type':'TEXT','required':True,'classification':'NORMAL'},
        {'key':'quantity','label':'Quantity collected','field_type':'DECIMAL','required':True,'classification':'NORMAL'},
        {'key':'unit','label':'Unit (for example kg, litres or items)','field_type':'TEXT','required':True,'classification':'NORMAL'},
        {'key':'notes','label':'Collection notes','field_type':'LONG_TEXT','required':False,'classification':'NORMAL'}]},
    {'code':'vehicle-request','name':'Vehicle request','category':'REQUEST','allow_drafts':True,'fields':[
        {'key':'destination','label':'Destination','field_type':'TEXT','required':True,'classification':'NORMAL'},
        {'key':'travel_date','label':'Travel date','field_type':'DATE','required':True,'classification':'NORMAL'},
        {'key':'purpose','label':'Purpose','field_type':'LONG_TEXT','required':True,'classification':'NORMAL'},
        {'key':'notes','label':'Notes','field_type':'LONG_TEXT','required':False,'classification':'NORMAL'}]},
    {'code':'daily-report','name':'Daily report','category':'DAILY_REPORT','allow_drafts':True,'fields':[
        {'key':'work_completed','label':'Work completed','field_type':'LONG_TEXT','required':True,'classification':'NORMAL'},
        {'key':'blockers','label':'Blockers','field_type':'LONG_TEXT','required':False,'classification':'NORMAL'}]},
    {'code':'inspection','name':'Inspection checklist','category':'INSPECTION','allow_drafts':True,'fields':[
        {'key':'site','label':'Site','field_type':'TEXT','required':True,'classification':'NORMAL'},
        {'key':'passed','label':'Inspection passed','field_type':'BOOLEAN','required':False,'classification':'NORMAL'},
        {'key':'findings','label':'Findings','field_type':'LONG_TEXT','required':True,'classification':'NORMAL'}]},
]



def question(key, label, kind='TEXT', required=True, **extra):
    field = dict(key=key, label=label, field_type=kind, required=required, classification='NORMAL')
    field.update(extra)
    return field


def design(code, name, category, description, fields):
    return dict(code=code, name=name, category=category, description=description,
                allow_drafts=True, fields=fields)


# Company copies remain drafts: these designs never assign people or publish themselves.
STARTERS += [
    design('weekly-progress', 'Weekly progress report', 'WEEKLY_REPORT',
           'Employees record results, challenges and next steps for their supervisor.', [
        question('week_start', 'Week beginning', 'DATE'), question('results', 'Results this week', 'LONG_TEXT'),
        question('challenges', 'Challenges and support needed', 'LONG_TEXT', False), question('next_steps', 'Next steps', 'LONG_TEXT')]),
    design('branch-summary', 'Branch operations summary', 'MONTHLY_REPORT',
           'Branch managers summarise performance and support needed for headquarters.', [
        question('period_start', 'Period starting', 'DATE'), question('period_end', 'Period ending', 'DATE'),
        question('results', 'Branch results', 'LONG_TEXT'), question('issues', 'Issues and risks', 'LONG_TEXT', False),
        question('support', 'Support requested from headquarters', 'LONG_TEXT', False)]),
    design('material-request', 'Request materials from headquarters', 'REQUEST',
           'A branch requests supplies. Assign a headquarters reviewer before publishing.', [
        question('items', 'Items, quantities and units needed', 'LONG_TEXT', help_text='List each item on a separate line with its quantity and unit.'),
        question('purpose', 'Why are these materials needed?', 'LONG_TEXT'), question('needed_by', 'Needed by', 'DATE'),
        question('delivery_location', 'Delivery location'), question('priority', 'Priority', 'SELECT', options=[{'value':v,'label':v.title()} for v in ['normal','urgent']])]),
    design('material-dispatch', 'Materials dispatch / delivery note', 'DELIVERY',
           'Stores or logistics records materials sent to a branch against an approved request.', [
        question('request_reference', 'Approved request reference'), question('dispatch_date', 'Dispatch date', 'DATE'),
        question('destination', 'Receiving branch or location'), question('items_sent', 'Items, quantities and units sent', 'LONG_TEXT'),
        question('delivery_reference', 'Delivery or transport reference', required=False), question('notes', 'Delivery instructions', 'LONG_TEXT', False)]),
    design('material-receipt', 'Confirm materials received', 'DELIVERY',
           'The receiving branch confirms deliveries, missing items and damage.', [
        question('request_reference', 'Request reference'), question('delivery_reference', 'Delivery reference'),
        question('received_date', 'Date received', 'DATE'), question('items_received', 'Items, quantities and units received', 'LONG_TEXT'),
        question('discrepancies', 'Missing or damaged items', 'LONG_TEXT', False), question('condition', 'Delivery condition', 'SELECT',
            options=[{'value':'complete','label':'Complete and in good condition'},{'value':'partial','label':'Partial delivery'},{'value':'damaged','label':'Damage or discrepancy'}])]),
    design('material-return', 'Return materials', 'DELIVERY',
           'Record items returned, the reason and the receiving location.', [
        question('original_reference', 'Original request or delivery reference'), question('return_date', 'Return date', 'DATE'),
        question('items', 'Items, quantities and units returned', 'LONG_TEXT'), question('reason', 'Reason for return', 'LONG_TEXT'), question('destination', 'Return destination')]),
    design('payment-collection', 'Payment collection record', 'COLLECTION',
           'Record an individual collection for review by the assigned finance reviewer.', [
        question('collection_date', 'Collection date', 'DATE'), question('reference', 'Receipt or payment reference'),
        question('amount', 'Amount collected', 'DECIMAL'), question('currency', 'Currency'), question('method', 'Payment method', 'SELECT',
            options=[{'value':v,'label':label} for v,label in [('cash','Cash'),('bank','Bank transfer'),('mobile','Mobile payment'),('other','Other')]]),
        question('purpose', 'What was the payment for?', 'LONG_TEXT')]),
    design('collection-summary', 'Daily collections summary', 'COLLECTION',
           'Summarise daily collections and differences for the responsible manager.', [
        question('date', 'Collection day', 'DATE'), question('total', 'Total collected', 'DECIMAL'), question('currency', 'Currency'),
        question('references', 'Included receipt references', 'LONG_TEXT'), question('differences', 'Differences or unresolved collections', 'LONG_TEXT', False)]),
    design('expense-request', 'Expense approval request', 'REQUEST',
           'Request approval before incurring a company expense.', [
        question('purpose', 'Expense purpose', 'LONG_TEXT'), question('amount', 'Estimated amount', 'DECIMAL'),
        question('currency', 'Currency'), question('needed_by', 'Needed by', 'DATE'), question('details', 'Supporting details', 'LONG_TEXT', False)]),
    design('purchase-request', 'Purchase request', 'REQUEST',
           'Request goods or services for review by the purchasing approver.', [
        question('items', 'Goods or services, quantities and units', 'LONG_TEXT'), question('purpose', 'Business purpose', 'LONG_TEXT'),
        question('estimated_cost', 'Estimated total cost', 'DECIMAL', False), question('currency', 'Currency', required=False),
        question('needed_by', 'Needed by', 'DATE'), question('supplier', 'Suggested supplier', required=False)]),
    design('reimbursement', 'Expense reimbursement', 'REQUEST',
           'Employees submit expenses already paid. Restrict answers to the employee and authorized reviewers.', [
        question('expense_date', 'Expense date', 'DATE'), question('purpose', 'Business purpose', 'LONG_TEXT'),
        question('amount', 'Amount paid', 'DECIMAL'), question('currency', 'Currency'), question('receipt_reference', 'Receipt reference')]),
    design('leave-request', 'Leave request', 'REQUEST',
           'Employees request leave from their supervisor. Do not collect medical details in this general form.', [
        question('start_date', 'First day of leave', 'DATE'), question('end_date', 'Last day of leave', 'DATE'),
        question('leave_type', 'Leave type', 'SELECT', options=[{'value':v,'label':label} for v,label in [('annual','Annual leave'),('personal','Personal leave'),('other','Other')]]),
        question('handover', 'Work handover arrangements', 'LONG_TEXT', False)]),
    design('attendance-correction', 'Attendance correction', 'REQUEST',
           'Request correction of an attendance entry from the responsible supervisor.', [
        question('date', 'Attendance date', 'DATE'), question('correction', 'Correction requested', 'LONG_TEXT'), question('reason', 'Reason', 'LONG_TEXT')]),
    design('employee-service', 'Employee service request', 'REQUEST',
           'Request an administrative service. Route it to the appropriate company office.', [
        question('service', 'Service needed'), question('details', 'Request details', 'LONG_TEXT'), question('needed_by', 'Needed by', 'DATE', False)]),
    design('stock-movement', 'Stock movement', 'PRODUCTION',
           'Record movement between stores or locations, with quantities and references.', [
        question('date', 'Movement date', 'DATE'), question('from_location', 'From location'), question('to_location', 'To location'),
        question('items', 'Items, quantities and units moved', 'LONG_TEXT'), question('reference', 'Related request or delivery reference', required=False)]),
    design('stock-count', 'Stock count', 'INSPECTION',
           'Record counted stock, expected quantities and discrepancies for stores review.', [
        question('date', 'Count date', 'DATE'), question('location', 'Store or location'),
        question('counts', 'Items, units, expected quantities and counted quantities', 'LONG_TEXT'), question('differences', 'Discrepancies and explanation', 'LONG_TEXT', False)]),
    design('equipment-issue', 'Equipment issue and return', 'COLLECTION',
           'Track equipment handed over or returned to stores.', [
        question('date', 'Handover date', 'DATE'), question('action', 'Handover type', 'SELECT', options=[{'value':'issue','label':'Issue equipment'},{'value':'return','label':'Return equipment'}]),
        question('equipment', 'Equipment and asset reference'), question('holder', 'Responsible person or position'), question('condition', 'Equipment condition', 'LONG_TEXT')]),
    design('maintenance-request', 'Maintenance request', 'MAINTENANCE',
           'Report equipment or premises needing maintenance to the responsible team.', [
        question('location', 'Location'), question('equipment', 'Equipment or area'), question('problem', 'Problem and impact', 'LONG_TEXT'),
        question('urgent', 'Urgent safety concern?', 'BOOLEAN', False), question('needed_by', 'Requested completion date', 'DATE', False)]),
    design('incident-report', 'Incident report', 'INCIDENT',
           'Record an operational incident. Configure restricted access before collecting sensitive personal details.', [
        question('date', 'Incident date', 'DATE'), question('location', 'Location'), question('summary', 'What happened?', 'LONG_TEXT'),
        question('action', 'Immediate action taken', 'LONG_TEXT'), question('follow_up', 'Follow-up needed', 'LONG_TEXT', False)]),
]


for material_design in STARTERS:
    if material_design['code'] in {'material-request','material-dispatch','material-receipt','material-return'}:
        for field in material_design['fields']:
            if field['key'] in {'items','items_sent','items_received'}:
                field.update(key='items',label='Items and quantities',field_type='ITEM_LIST',required=True,help_text='Add each item with its quantity and unit.')


# Answer guidance travels with each company-owned copy of a ready-made form.
_GUIDANCE = {
    'blockers': ('Describe anything that delayed or prevented your work, and the help you need. Leave blank if there were no difficulties.', 'Example: Work stopped because packaging supplies ran out. Please send more supplies.'),
    'work_completed': ('Describe what you did today and the result. Include quantities where useful.', 'Example: Packed 120 boxes and delivered 100 to the branch store.'),
    'results': ('Summarise completed work and measurable results for this reporting period.', 'Example: Completed 40 deliveries; 38 were on time.'),
    'next_steps': ('Describe what you plan to do next and any help or resources needed.', 'Example: Complete the remaining deliveries tomorrow morning.'),
    'challenges': ('Explain difficulties during this period and the support needed to resolve them.', 'Example: Two deliveries were delayed; a replacement vehicle is needed.'),
    'issues': ('Describe problems or risks that need attention. Leave blank if there are none.', 'Example: Stock may run out before the next delivery.'),
    'support': ('Describe what headquarters should provide or decide, and when it is needed.', 'Example: Please approve additional packaging supplies for next week.'),
    'purpose': ('Explain why this work, payment or request is needed and what it will achieve.', 'Example: Supplies are needed to complete this week’s production.'),
    'notes': ('Add useful details that are not already covered above. Leave blank if none.', 'Example: Call the receiving office before arrival.'),
    'destination': ('Name the branch, office or address where the journey or delivery ends.', 'Example: Food Production branch, main receiving store.'),
    'delivery_location': ('Give the receiving branch and the precise delivery point.', 'Example: Food Production branch, loading bay beside the main store.'),
    'site': ('Name the place or facility being inspected.', 'Example: Headquarters, ground-floor store.'),
    'findings': ('Describe what you checked, what you found and any corrective action needed.', 'Example: Checked fire exits; one exit was obstructed and must be cleared.'),
    'passed': ('Choose Yes if the inspection met the required checks, or No if action is needed.', ''),
    'priority': ('Choose Urgent only when a delay would seriously affect work or safety.', ''),
    'request_reference': ('Use the reference shown on the related request. Copy it exactly so the records can be matched.', 'Example: MAT-2026-0042'),
    'delivery_reference': ('Use the delivery-note or transport reference supplied with the materials.', 'Example: DEL-2026-0018'),
    'original_reference': ('Copy the reference of the original request or delivery being returned.', 'Example: DEL-2026-0018'),
    'reference': ('Enter the receipt or related record reference so this entry can be traced.', 'Example: REC-2026-0081'),
    'references': ('List the receipts included in this total, one reference per line.', 'Example: REC-2026-0081, REC-2026-0082'),
    'receipt_reference': ('Copy the receipt number for the expense you paid.', 'Example: REC-2026-0081'),
    'currency': ('Enter the currency used for the amount, such as RWF, USD or EUR.', 'Example: RWF'),
    'amount': ('Enter the amount as a number. Use the currency field to identify the currency.', 'Example: 25000'),
    'total': ('Add the included collections and enter their total as a number.', 'Example: 150000'),
    'estimated_cost': ('Enter your best estimate of the total purchase cost. Leave blank if it is not yet known.', 'Example: 75000'),
    'item': ('Name the goods or material collected clearly.', 'Example: Cement'),
    'quantity': ('Enter the number or measured quantity. Specify its unit in the next field.', 'Example: 25'),
    'unit': ('State how the quantity is measured, such as pieces, bags, kg or litres.', 'Example: bags'),
    'items': ('List the goods, quantities and units. For services, describe the service needed.', 'Example: Cement — 25 bags; paint — 10 litres'),
    'differences': ('Explain any difference between what was expected and what was recorded. Leave blank if the amounts or counts agree.', 'Example: Counted 48 items; the record shows 50. Two items need checking.'),
    'discrepancies': ('List missing, damaged or incorrect items and their quantities. Leave blank if everything matches.', 'Example: Two bags were missing and one bag was damaged.'),
    'reason': ('Explain why this request, correction or return is needed.', 'Example: The recorded quantity does not match the items received.'),
    'details': ('Provide the information the responsible person needs to understand and process your request.', 'Example: Include the item specification, quantity and intended use.'),
    'supplier': ('Name a supplier you suggest. Leave blank if you have no preference.', 'Example: Your company’s approved supplier'),
    'handover': ('Describe who will cover your work and where they can find necessary information.', 'Example: My supervisor will cover deliveries; records are in the shared folder.'),
    'correction': ('Describe the recorded entry and the change you are requesting.', 'Example: The entry shows absent; please change it to present for the morning shift.'),
    'service': ('Name the administrative help you need.', 'Example: Employment confirmation letter'),
    'from_location': ('Name the store or location sending the items.', 'Example: Headquarters, main store'),
    'to_location': ('Name the store or location receiving the items.', 'Example: Food Production branch store'),
    'location': ('Name the branch, building or work area concerned.', 'Example: Food Production branch, packing area'),
    'counts': ('For each item, include its unit, expected quantity and actual counted quantity.', 'Example: Cement; bags; expected 50; counted 48'),
    'equipment': ('Name the equipment and include its asset number if available.', 'Example: Delivery van, asset VEH-004'),
    'holder': ('Name the person or position responsible for the equipment.', 'Example: Branch stores officer'),
    'condition': ('Describe the equipment condition and any damage or faults.', 'Example: Working normally; small scratch on the left panel.'),
    'problem': ('Explain what is wrong and how it affects work or safety.', 'Example: The packing machine stops repeatedly, delaying production.'),
    'urgent': ('Choose Yes if the problem requires immediate safety attention. Follow your company’s emergency procedure when needed.', ''),
    'summary': ('Describe what happened, where it happened and its effect. Include facts rather than assumptions.', 'Example: A water leak interrupted work in the store.'),
    'action': ('Describe what was done immediately to deal with the incident.', 'Example: Isolated the affected area and informed the supervisor.'),
    'follow_up': ('Describe further action needed and who should take it.', 'Example: Maintenance should repair the pipe before the area reopens.'),
}
for _starter in STARTERS:
    if _starter['code'] == 'daily-report':
        _starter['description'] = 'Record today’s completed work, difficulties and plans for your supervisor.'
        _starter['fields'].insert(0, question('report_date', 'Day being reported', 'DATE'))
        _starter['fields'].append(question('next_steps', 'Plans for the next working day', 'LONG_TEXT', False))
    elif _starter['code'] == 'vehicle-request':
        _starter['description'] = 'Request a company vehicle for a work journey. Provide the date, destination and reason.'
    elif _starter['code'] == 'collection-record':
        _starter['description'] = 'Record goods or materials collected, including their quantity, unit and collection date.'
    elif _starter['code'] == 'inspection':
        _starter['description'] = 'Record an inspection location, its outcome and any action needed.'
    for _field in _starter['fields']:
        if _field['key'] == 'blockers':
            _field['label'] = 'Difficulties and support needed'
        if _field['field_type'] == 'ITEM_LIST':
            _field['help_text'] = 'Add one row per item. Enter its name, quantity and unit, for example Cement, 25, bags.'
        elif _field['field_type'] == 'DATE':
            _field['help_text'] = 'Choose the date this entry refers to.'
            if _field['key'] == 'needed_by':
                _field['help_text'] = 'Choose the latest date you need the requested goods, service or work completed.'
        elif _field['field_type'] in {'SELECT', 'MULTISELECT'}:
            _field['help_text'] = 'Choose the option that describes this entry.'
            if _field['key'] == 'priority':
                _field['help_text'] = _GUIDANCE['priority'][0]
        elif _field['key'] in _GUIDANCE:
            _field['help_text'], _field['placeholder'] = _GUIDANCE[_field['key']]


# Complete forms share entry context; the server supplies these defaults.
for _starter in STARTERS:
    _code = _starter['code']
    _fields = _starter['fields']
    if _code == 'collection-record':
        _starter['name'] = 'Goods collection form'
        _fields[:] = [field for field in _fields if field['key'] not in {'item','quantity','unit'}]
        _fields.insert(1, question('collection_type','Collection type','SELECT',options=[
            {'value':'supplier','label':'Collection from a supplier'},
            {'value':'company_store','label':'Collection from a company store'},
            {'value':'returned_goods','label':'Collection of returned goods'},
            {'value':'other','label':'Other collection'}],help_text='Choose where or why the goods are being collected.'))
        _fields.insert(2, question('items','Goods collected','ITEM_LIST',help_text='Add each item, its collected quantity and unit, for example Cement, 25, bags.'))
    elif _code == 'payment-collection':
        _starter['name'] = 'Payment collection form'
        _fields.insert(1, question('collection_type','Collection type','SELECT',options=[
            {'value':'sale','label':'Sales payment'}, {'value':'fee','label':'Service fee'},
            {'value':'outstanding','label':'Outstanding payment'}, {'value':'other','label':'Other payment'}],help_text='Choose what this payment is being collected for.'))
    _context = [question('recorded_by', 'Collector’s name' if _code in {'collection-record','payment-collection'} else 'Your name', classification='PERSONAL',
        help_text='Filled from your signed-in profile. It cannot be changed in this form.', validation_rules={'default_source':'USER_NAME','section':'About this entry'}),
        question('company_name','Company',classification='PERSONAL',help_text='Filled from your current company workspace.',validation_rules={'default_source':'COMPANY_NAME','section':'About this entry'})]
    if not any(field['key'] in {'report_date','collection_date','date','dispatch_date','received_date','return_date','expense_date'} for field in _fields):
        _context.append(question('recorded_on','Entry date','DATE',help_text='Starts with today’s date in your company’s timezone. Change it if recording an earlier entry.',validation_rules={'default_source':'TODAY','section':'About this entry'}))
    if not any(field['key'] == 'location' for field in _fields):
        _context.append(question('work_location','Collection location' if _code in {'collection-record','payment-collection'} else 'Your branch or work location',help_text='Starts with your assigned branch. Enter the work location if no branch is assigned, or correct it when needed.',placeholder='Example: Food Production branch, main store',validation_rules={'default_source':'BRANCH_NAME','section':'About this entry'}))
    _starter['fields'] = _context + _fields
    for _field in _starter['fields']:
        _rules = _field.setdefault('validation_rules', {})
        _rules.setdefault('section', 'Collection details' if _code in {'collection-record','payment-collection','collection-summary'} else 'Form details')
        if _field['key'] in {'report_date','collection_date','date','dispatch_date','received_date','return_date','expense_date'}:
            _rules.update(default_source='TODAY', section='About this entry')
            _field['help_text'] = 'Filled with today’s date in your company’s timezone. Change it if this entry relates to another date.'
        if _field['key'] == 'location':
            _rules.update(default_source='BRANCH_NAME',section='About this entry')
        if _field['key'] == 'currency':
            _rules['default_source'] = 'COMPANY_CURRENCY'
        if _field['key'] in {'notes','details','next_steps','support','challenges','blockers','differences','discrepancies','follow_up'}:
            _rules['section'] = 'Additional details'
# Non-negative monetary defaults apply to new library copies, not existing entries.
for _starter in STARTERS:
    if _starter['code'] in {'payment-collection', 'collection-summary', 'expense-request', 'purchase-request', 'reimbursement'}:
        for _field in _starter['fields']:
            if _field['field_type'] == 'DECIMAL':
                _field.setdefault('validation_rules', {}).setdefault('min', 0)
