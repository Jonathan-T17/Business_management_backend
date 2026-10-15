import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion as deletion

class Migration(migrations.Migration):
    dependencies = [('forms_engine','0009_form_position_audience'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name='formtemplate', name='source_starter', field=models.CharField(max_length=100, blank=True, editable=False)),
        migrations.CreateModel(name='MaterialJourney', fields=[('id',models.BigAutoField(primary_key=True,serialize=False)),('items',models.JSONField(default=list)),('approved',models.JSONField(default=dict)),('submission',models.OneToOneField(to='forms_engine.formsubmission',on_delete=deletion.PROTECT,related_name='material_journey'))]),
        migrations.CreateModel(name='MaterialMovement', fields=[('id',models.BigAutoField(primary_key=True,serialize=False)),('stage',models.CharField(max_length=20,choices=[('DISPATCH','Dispatch'),('RECEIPT','Receipt'),('RETURN','Return')])),('reference',models.UUIDField(default=uuid.uuid4,unique=True)),('quantities',models.JSONField(default=dict)),('note',models.TextField(blank=True)),('schema_snapshot',models.JSONField(default=dict)),('answers',models.JSONField(default=dict)),('created_at',models.DateTimeField(auto_now_add=True)),('journey',models.ForeignKey(to='forms_engine.materialjourney',on_delete=deletion.PROTECT,related_name='movements')),('actor',models.ForeignKey(to=settings.AUTH_USER_MODEL,on_delete=deletion.PROTECT)),('template',models.ForeignKey(to='forms_engine.formtemplate',on_delete=deletion.PROTECT))]),
    ]
