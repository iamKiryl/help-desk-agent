from pathlib import Path
from pprint import pprint
from datetime import datetime
from decimal import Decimal
import json
import re

BOOKINGS_PATH = Path(__file__).resolve().parent / "data" / "bookings.json"
CURRENT_TIME = datetime.fromisoformat("2026-06-10T09:00:00+02:00")
POLICIES_PATH = Path(__file__).resolve().parent / "data" / "policies"

def get_booking(booking_id: str) -> dict:
    with BOOKINGS_PATH.open(encoding='utf-8') as file:
        bookings = json.load(file)
    for booking in bookings:
        if booking["id"] == booking_id:
            return {"found": True, "booking": booking}
    return {"found": False, "booking_id": booking_id}

def calculate_refund(booking_id: str) -> dict:
    result = get_booking(booking_id)

    if not result["found"]:
        return result

    booking = result["booking"]

    if booking["status"] != "confirmed":
        return {
            "found": True,
            "booking_id": booking_id,
            "can_cancel": False,
            "reason": f"Booking status is {booking['status']}",
            "total_refund_eur": "0.00",
        }

    start = datetime.fromisoformat(booking["start"])
    hours_before_start = (start - CURRENT_TIME).total_seconds() / 3600

    if hours_before_start >= 48:
        refund_rate = Decimal("1")
    elif hours_before_start >= 24:
        refund_rate = Decimal("0.5")
    else:
        refund_rate = Decimal("0")

    rental_price = Decimal(str(booking["rental_price_eur"]))
    deposit = Decimal(str(booking["deposit_eur"]))

    rental_refund = rental_price * refund_rate
    total_refund = rental_refund + deposit

    return {
        "found": True,
        "booking_id": booking_id,
        "can_cancel": True,
        "hours_before_start": hours_before_start,
        "rental_refund_percent": int(refund_rate * 100),
        "rental_refund_eur": f"{rental_refund:.2f}",
        "deposit_refund_eur": f"{deposit:.2f}",
        "booking_fee_refund_eur": "0.00",
        "total_refund_eur": f"{total_refund:.2f}",
        "rental_refund_method": (
            "new_voucher" if booking["paid_with"] == "voucher" else "card"
        ),
        "deposit_refund_method": booking["paid_with"],
    }

def search_policies(query: str) -> dict:
    stop_words = {
        "a", "an", "the", "is", "are", "do", "does",
        "i", "my", "you", "your", "what", "how",
        "can", "to", "of", "for", "and", "in",
    }

    query_words = set(re.findall(r"[a-z0-9]+", query.lower()))
    query_words -= stop_words

    matches = []

    for path in sorted(POLICIES_PATH.glob("*.md")):
        document = path.read_text(encoding="utf-8")

        for section in re.split(r"(?m)^## ", document)[1:]:
            title, _, content = section.partition("\n")
            text = f"{title}\n{content}".strip()

            section_words = set(re.findall(r"[a-z0-9]+", text.lower()))
            score = len(query_words & section_words)

            if score > 0:
                matches.append({
                    "source": path.name,
                    "section": title.strip(),
                    "text": text,
                    "score": score,
                })

    matches.sort(key=lambda item: item["score"], reverse=True)

    return {"query": query, "results": matches[:3]}

if __name__ == "__main__":
    pprint(search_policies("opening hours open Saturday"))
    pprint(search_policies("cancellation refund"))
    pprint(search_policies("quantum physics"))
