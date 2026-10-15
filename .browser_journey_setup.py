from datetime import time, timedelta
from django.db import transaction
from django.utils import timezone
from users.models import User
from workflows.models import WorkflowDefinition, WorkflowStepDefinition
from forms_engine.models import FormTemplate, FormField
from forms_engine.versioning import FormTemplateVersionService
from reporting_schedules.models import ReportingSchedule, ReportingObligation
from security.services import create_audit_log

with transaction.atomic():
 admin=User.objects.get(full_name='Jonathan TWIZE',role='ADMIN',company__name='Business Group Ltd')
 author=User.objects.get(full_name='Honore DUSABAMAHORO',company=admin.company)
 reviewer=User.objects.get(full_name='Uwera Chantal',company=admin.company)
 code='browser-journey-20261001'
 workflow,created=WorkflowDefinition.objects.get_or_create(company=admin.company,code=code,defaults={'name':'TEST - Food Production report review','target_type':'FORM_SUBMISSION','created_by':admin})
 if created:
  WorkflowStepDefinition.objects.create(workflow=workflow,name='TEST - Branch manager review',order=1,recipient_type='USER',recipient_user=reviewer,notify_email=False,notify_in_app=True)
 template,created=FormTemplate.objects.get_or_create(company=admin.company,code=code,version=1,defaults={'name':'TEST - Food Production daily report','description':'Browser verification only. Sample information, not operational records.','category':'DAILY_REPORT','branch':author.branch,'audience_user_ids':[str(author.pk),str(reviewer.pk)],'workflow':workflow,'created_by':admin})
 if created:
  FormField.objects.create(template=template,key='work_completed',label='Work completed (test only)',field_type='LONG_TEXT',required=True,order=1)
  FormField.objects.create(template=template,key='blockers',label='Blockers (test only)',field_type='LONG_TEXT',order=2)
  template=FormTemplateVersionService.publish(template=template,actor=admin)
 today=timezone.localdate()
 schedule,created=ReportingSchedule.objects.get_or_create(company=admin.company,name='TEST - One-day employee reporting check',defaults={'template':template,'frequency':'DAILY','target_type':'USER','target_user':author,'start_date':today,'end_date':today,'due_time':time(23,59),'created_by':admin})
 obligation,created=ReportingObligation.objects.get_or_create(company=admin.company,schedule=schedule,user=author,reporting_date=today,defaults={'due_at':timezone.now()+timedelta(hours=12),'morning_reminder_sent':True,'final_reminder_sent':True})
 if created:
  create_audit_log(user=admin,company=admin.company,action='CREATE',obj=obligation,description='User-authorized TEST reporting journey assigned to Honore with Uwera as reviewer.')
 print({'template':str(template.pk),'obligation':str(obligation.pk),'status':obligation.status})
