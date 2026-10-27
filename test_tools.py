import unittest

from tools import get_booking, calculate_refund, search_policies


class BookingTests(unittest.TestCase):
    def test_existing_booking(self):
        result = get_booking("CW-1002")

        self.assertTrue(result["found"])
        self.assertEqual(result["booking"]["id"], "CW-1002")

    def test_unknown_booking(self):
        result = get_booking("CW-9999")

        self.assertFalse(result["found"])


class RefundTests(unittest.TestCase):
    def test_refund_amounts(self):
        cases = [
            # Booking ID, rental refund percentage, total refund
            ("CW-1001", 100, "90.00"),
            ("CW-1002", 50, "340.00"),
            ("CW-1003", 0, "50.00"),
            ("CW-1007", 100, "186.00"),  # Exactly 48 hours
            ("CW-1010", 50, "170.00"),   # Exactly 24 hours
        ]

        for booking_id, percent, total in cases:
            with self.subTest(booking_id=booking_id):
                result = calculate_refund(booking_id)

                self.assertTrue(result["can_cancel"])
                self.assertEqual(result["rental_refund_percent"], percent)
                self.assertEqual(result["total_refund_eur"], total)
                self.assertEqual(result["booking_fee_refund_eur"], "0.00")

    def test_non_cancellable_statuses(self):
        for booking_id in ["CW-1005", "CW-1006", "CW-1008"]:
            with self.subTest(booking_id=booking_id):
                result = calculate_refund(booking_id)

                self.assertFalse(result["can_cancel"])
                self.assertEqual(result["total_refund_eur"], "0.00")

    def test_voucher_refund(self):
        result = calculate_refund("CW-1004")

        self.assertEqual(result["rental_refund_method"], "new_voucher")
        self.assertEqual(result["deposit_refund_method"], "voucher")
        self.assertEqual(result["rental_refund_eur"], "23.00")
        self.assertEqual(result["deposit_refund_eur"], "50.00")
        self.assertEqual(result["total_refund_eur"], "73.00")

    def test_unknown_booking(self):
        result = calculate_refund("CW-9999")

        self.assertFalse(result["found"])

class PolicySearchTests(unittest.TestCase):
    def test_opening_hours(self):
        results = search_policies("opening hours open Saturday")["results"]

        self.assertTrue(results)
        self.assertEqual(results[0]["source"], "faq.md")
        self.assertEqual(results[0]["section"], "When are you open?")
        self.assertIn("08:00–20:00", results[0]["text"])

    def test_cancellation_rules(self):
        results = search_policies("cancellation refund")["results"]

        cancellation = next(
            (
                item for item in results
                if item["section"] == "Cancelling a booking"
            ),
            None,
        )

        self.assertIsNotNone(cancellation)
        self.assertIn("48 hours", cancellation["text"])
        self.assertIn("50%", cancellation["text"])

    def test_unrelated_query(self):
        self.assertEqual(
            search_policies("quantum physics")["results"],
            [],
        )

    def test_empty_query(self):
        self.assertEqual(search_policies("")["results"], [])

    def test_opening_hours_queries_from_evaluation(self):
        queries = [
            "opening hours June",
            "opening hours shop hours schedule",
        ]

        for query in queries:
            with self.subTest(query=query):
                results = search_policies(query)["results"]

                self.assertTrue(results)
                self.assertEqual(
                    results[0]["section"],
                    "When are you open?",
                )
                self.assertIn("08:00–20:00", results[0]["text"])

    def test_age_limit_query_from_evaluation(self):
        results = search_policies(
            "age limit e-bike rent"
        )["results"]

        self.assertTrue(results)
        self.assertEqual(results[0]["section"], "Are there age limits?")
        self.assertIn("from 16 years old", results[0]["text"])

if __name__ == "__main__":
    unittest.main()
