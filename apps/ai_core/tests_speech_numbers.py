from django.test import SimpleTestCase

from apps.ai_core.speech_numbers import normalize_spoken_phone


class SpokenPhoneTests(SimpleTestCase):
    def test_digit_fidelity_and_names(self):
        cases = [
            ("Запиши Ивана Иванова телефон плюс семь семь ноль два два два два два два два два на консультацию к Анне",
             "Запиши Ивана Иванова телефон +77022222222 на консультацию к Анне"),
            ("Анна, телефон: плюс семь семь ноль один ноль ноль ноль два ноль три ноль.",
             "Анна, телефон: +77010002030."),
            ("Телефон восемь семь ноль пять один два три четыре пять шесть семь",
             "Телефон 87051234567"),
            ("Phone number plus one two zero two five five five zero one four seven.",
             "Phone number +12025550147."),
            ("Телефон нөмірі плюс жеті жеті нөл бір екі үш төрт бес алты жеті сегіз",
             "Телефон нөмірі +77012345678"),
        ]
        for before, after in cases:
            with self.subTest(before=before):
                self.assertEqual(normalize_spoken_phone(before), after)
                self.assertEqual(normalize_spoken_phone(after), after)

    def test_ambiguous_grouped_short_or_unlabelled_numbers_unchanged(self):
        cases = [
            "телефон плюс семь семь ноль один двести тридцать четыре",
            "телефон один два три четыре пять шесть семь двадцать",
            "телефон " + "семь " * 16,
            "телефон один два три",
            "добавь заметку один два три четыре пять шесть семь",
            "на семь ноября две тысячи тридцатого года",
            "телефон +77012345678", "Анна Смирнова",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(normalize_spoken_phone(text), text)
