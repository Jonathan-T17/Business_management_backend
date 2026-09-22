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
