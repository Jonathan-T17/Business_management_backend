from core.classification import max_classification
class DocumentClassificationResolver:
    @classmethod
    def resolve(cls,document):
        category=getattr(document,'category',None); c=getattr(category,'classification',None)
        if category and getattr(category,'sensitive',False) and not c:c='MANAGEMENT_CONFIDENTIAL'
        return max_classification(getattr(document,'classification','NORMAL'),c)
class AttachmentClassificationResolver:
    @classmethod
    def resolve(cls,attachment):
        parent=attachment.content_object; return max_classification(getattr(attachment,'classification','NORMAL'),getattr(parent,'classification',None),getattr(parent,'sensitivity',None))
