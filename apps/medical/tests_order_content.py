from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from .order_content import ORDER_KINDS, validate_order_content


class OrderContentTests(SimpleTestCase):
    def test_each_type_keeps_literal_text_without_inventing_medication_fields(self):
        for kind in ORDER_KINDS:
            with self.subTest(kind=kind):
                content = {"kind": kind, "text": "Synthetic оқу", "medication": {}}
                self.assertEqual(validate_order_content(content), content)

    def test_medication_fields_are_copied_without_changing_clinical_input(self):
        source = {"kind": "medication", "text": "", "medication": {"dose": "Synthetic literal value"}}
        clean = validate_order_content(source)
        source["medication"]["dose"] = "Changed"
        self.assertEqual(clean["medication"]["dose"], "Synthetic literal value")

    def test_unknown_incompatible_and_unbounded_input_is_rejected(self):
        base = {"kind": "other", "text": "", "medication": {}}
        for content in (None, {}, {**base, "patient_id": 1}, {**base, "kind": []},
                        {**base, "kind": "unknown"}, {**base, "text": False},
                        {**base, "text": "x" * 32769}, {**base, "medication": []},
                        {**base, "medication": {"dose": "Synthetic"}},
                        {**base, "kind": "medication", "medication": {"unknown": ""}},
                        {**base, "kind": "medication", "medication": {"dose": False}},
                        {**base, "kind": "medication", "medication": {"dose": "x" * 2001}}):
            with self.subTest(content=content), self.assertRaises(ValidationError):
                validate_order_content(content)
