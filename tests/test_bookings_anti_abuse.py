import pytest
from lib.bookings import (
    book_slot,
    get_active_customer_booking,
    cancel_booking,
    get_available_slots,
    _mock_bookings
)

@pytest.fixture(autouse=True)
def isolated_in_memory(monkeypatch):
    """Ensure tests run against isolated in-memory storage."""
    monkeypatch.setattr("lib.bookings.supabase_client", None)
    _mock_bookings.clear()
    yield
    _mock_bookings.clear()

@pytest.mark.asyncio
async def test_first_booking_succeeds():
    """Customer with no prior bookings should successfully book a slot."""
    res = await book_slot(
        client_id="test-client-uuid",
        customer_phone="919999999991",
        customer_name="Alice",
        date="2026-11-20",
        time="10:00 AM"
    )
    assert res["status"] == "success"
    assert res["booked"] is True
    assert "booking_id" in res

@pytest.mark.asyncio
async def test_anti_spam_prevents_multiple_active_bookings():
    """A customer cannot book multiple active slots to hijack the calendar."""
    # First booking
    res1 = await book_slot(
        client_id="test-client-uuid",
        customer_phone="919999999992",
        customer_name="Bob",
        date="2026-11-20",
        time="10:00 AM"
    )
    assert res1["booked"] is True

    # Attempt to book a second slot without rescheduling
    res2 = await book_slot(
        client_id="test-client-uuid",
        customer_phone="919999999992",
        customer_name="Bob",
        date="2026-11-21",
        time="02:00 PM",
        reschedule=False
    )
    assert res2["booked"] is False
    assert res2["status"] == "limit_reached"
    assert res2["can_reschedule"] is True
    assert "You already have a visit scheduled" in res2["message"]

@pytest.mark.asyncio
async def test_rescheduling_releases_old_slot_and_books_new():
    """When customer chooses to reschedule, old slot is freed and new slot is confirmed."""
    phone = "919999999993"
    # First booking on Nov 20 10:00 AM
    await book_slot(
        client_id="test-client-uuid",
        customer_phone=phone,
        customer_name="Charlie",
        date="2026-11-20",
        time="10:00 AM"
    )

    # Reschedule to Nov 21 02:00 PM
    res_reschedule = await book_slot(
        client_id="test-client-uuid",
        customer_phone=phone,
        customer_name="Charlie",
        date="2026-11-21",
        time="02:00 PM",
        reschedule=True
    )
    assert res_reschedule["booked"] is True
    assert res_reschedule["status"] == "rescheduled"

    # Verify old slot Nov 20 10:00 AM is now available for another customer
    res_other = await book_slot(
        client_id="test-client-uuid",
        customer_phone="919888888888",
        customer_name="Dave",
        date="2026-11-20",
        time="10:00 AM"
    )
    assert res_other["booked"] is True
    assert res_other["status"] == "success"
