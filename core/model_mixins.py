from django.db import models
from .classification import DataClassification
class ClassifiedModelMixin(models.Model):
    classification=models.CharField(max_length=40,choices=[(i.value,i.value.replace('_',' ').title()) for i in DataClassification],default=DataClassification.NORMAL,db_index=True)
    class Meta: abstract=True
