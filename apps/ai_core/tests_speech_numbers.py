from django.test import SimpleTestCase

from apps.ai_core.speech_numbers import ambiguous_spoken_phone, normalize_spoken_phone


class SpokenPhoneTests(SimpleTestCase):
    def test_plus_comma_preserves_repeated_zeroes(self):
        text = "Телефон плюс, жеті, жеті, нөл, бір, нөл, нөл, нөл, екі, нөл, үш, нөл."
        self.assertEqual(normalize_spoken_phone(text), "Телефон +77010002030.")

    def test_distorted_phone_labels_require_clarification(self):
        for text in ("Телефон номері дұрыс: жеті жеті нөл бір екі үш төрт бес алты жеті сегіз.",
                     "Telefon nömrə plus yeddi yeddi sıfır bir sıfır sıfır iki sıfır üç sıfır."):
            with self.subTest(text=text):
                self.assertTrue(ambiguous_spoken_phone(text))

    def test_phone_before_date_keeps_date_and_every_digit(self):
        phone = "плюс семь семь ноль екі екі екі екі екі екі екі екі"
        for suffix in (", 10 ноября 2030 года в 12 часов.", ", 9 қарашада сағат 12-де.",
                       "; 8 November 2030 at 10.", ", 10.11.2030 в 12:00."):
            before = "Телефон " + phone + suffix
            with self.subTest(suffix=suffix):
                self.assertEqual(normalize_spoken_phone(before), "Телефон +77022222222" + suffix)
                self.assertFalse(ambiguous_spoken_phone(before))

    def test_numeric_continuation_is_not_assumed_to_be_a_date(self):
        phone = "Телефон плюс семь семь ноль екі екі екі екі екі екі екі екі"
        for suffix in (", 10 11 12", ", 10 добавочный", ", 99 ноября", " 10 ноября", ", два ноября"):
            with self.subTest(suffix=suffix):
                self.assertEqual(normalize_spoken_phone(phone + suffix), phone + suffix)
        for count in (6, 16):
            text = "Телефон " + " ".join(["два"] * count) + ", 10 ноября 2030."
            self.assertEqual(normalize_spoken_phone(text), text)

    def test_typographic_label_separator_preserves_every_mixed_digit(self):
        for separator in ("—", "–", "-"):
            before = f"Жаңа клиент қос: имя — Әлихан Омаров, телефон {separator} плюс семь семь ноль бес бір два үш четыре бес шесть жеті."
            after = f"Жаңа клиент қос: имя — Әлихан Омаров, телефон {separator} +77051234567."
            with self.subTest(separator=separator):
                self.assertEqual(normalize_spoken_phone(before), after)
                self.assertFalse(ambiguous_spoken_phone(before))
        ambiguous = "Телефон — плюс семь семь ноль один двести тридцать четыре"
        self.assertEqual(normalize_spoken_phone(ambiguous), ambiguous)
        self.assertTrue(ambiguous_spoken_phone(ambiguous))

    def test_phone_word_count_is_not_completed_or_shortened_to_a_national_length(self):
        for repetitions in (6, 8):
            before = "Телефон нөмірі — плюс жеті жеті нөл бір " + " ".join(["екі"] * repetitions) + "."
            expected = "Телефон нөмірі — +7701" + "2" * repetitions + "."
            with self.subTest(repetitions=repetitions):
                self.assertEqual(normalize_spoken_phone(before), expected)

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
