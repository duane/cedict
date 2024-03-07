import unittest
import conversion


class TonePlacementBufMethods(unittest.TestCase):
    def test_tonable(self):
        self.assertTrue(conversion.is_tonable_char("a"))
        self.assertTrue(conversion.is_tonable_char("e"))
        self.assertTrue(conversion.is_tonable_char("i"))
        self.assertTrue(conversion.is_tonable_char("o"))
        self.assertTrue(conversion.is_tonable_char("u"))

    def test_has_tonable(self):
        b = conversion.TonePlacementBuf()
        b.append("i")
        self.assertTrue(b.has_tonable())

    def test_splice(self):
        b = conversion.TonePlacementBuf()
        b.append("i")
        self.assertEqual(b.spliced_tone(0, "\u0301"), "í")

    def test_spliced_combining_diacritic(self):
        self.assertEqual(
            conversion.TonePlacementBuf("i").spliced_combining_diacritic("\u0301"), "í"
        )

    def test_spliced_tone_digit(self):
        self.assertEqual(conversion.TonePlacementBuf("i").spliced_tone_digit("2"), "í")

    def test_idx_for_tone(self):
        self.assertEqual(conversion.idx_for_tone(list("ai")), 0)
        self.assertEqual(conversion.idx_for_tone(list("ao")), 0)

        self.assertEqual(conversion.idx_for_tone(list("ei")), 0)

        self.assertEqual(conversion.idx_for_tone(list("ia")), 1)
        self.assertEqual(conversion.idx_for_tone(list("iao")), 1)
        self.assertEqual(conversion.idx_for_tone(list("ie")), 1)
        self.assertEqual(conversion.idx_for_tone(list("io")), 1)
        self.assertEqual(conversion.idx_for_tone(list("iu")), 1)

        self.assertEqual(conversion.idx_for_tone(list("ou")), 0)

        self.assertEqual(conversion.idx_for_tone(list("ua")), 1)
        self.assertEqual(conversion.idx_for_tone(list("uai")), 1)
        self.assertEqual(conversion.idx_for_tone(list("ue")), 1)
        self.assertEqual(conversion.idx_for_tone(list("uo")), 1)
        self.assertEqual(conversion.idx_for_tone(list("ui")), 1)


class DigitToDiacriticTest(unittest.TestCase):
    def test_digit_to_diacritic(self):
        self.assertEqual(conversion.s_digit_to_diacritic("yi1"), "yī")
        self.assertEqual(conversion.s_digit_to_diacritic("yi2"), "yí")
        self.assertEqual(conversion.s_digit_to_diacritic("zhuang1"), "zhuāng")
        self.assertEqual(conversion.s_digit_to_diacritic("Zhuang4zu2"), "Zhuàngzú")


if __name__ == "__main__":
    unittest.main()
