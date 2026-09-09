from core.classification import max_classification
class OfficialRecordClassificationPolicy:
    @classmethod
    def classification_for_source(cls,source):
        category=getattr(source,'category',None); return max_classification(getattr(source,'classification',None),getattr(source,'sensitivity',None),getattr(category,'classification',None))
    @classmethod
    def validate_snapshot_ceiling(cls,*,source,record):
        source_c=cls.classification_for_source(source); record_c=getattr(record,'classification','NORMAL')
        if max_classification(source_c,record_c)!=record_c: raise ValueError('Official Record classification cannot be weaker than its source.')
