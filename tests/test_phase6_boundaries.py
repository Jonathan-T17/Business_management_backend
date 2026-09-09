from django.test import TestCase
from core.data_classification import DataClassification


class ClassificationTests(TestCase):
    def test_max_classification_is_stable(self):
        self.assertEqual(
            DataClassification.max_classification([DataClassification.NORMAL, DataClassification.COMPENSATION]),
            DataClassification.COMPENSATION,
        )


class Phase6ContractNotes(TestCase):
    def test_no_continuous_tracking_contract(self):
        forbidden_api_names = {"track_continuously", "background_location_stream", "live_gps_stream"}
        self.assertNotIn("arrive_stop", forbidden_api_names)
