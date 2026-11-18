"""
ARVANA Booking & Calendar System
Handles site visit scheduling with live availability checking.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import uuid
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("arvana.bookings")

# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL != "your_supabase_project_url":
    try:
        from supabase import create_client, Client
        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Bookings system connected to Supabase.")
    except Exception as e:
        logger.warning(f"Bookings system using in-memory fallback: {e}")

# In-memory fallback for local testing without Supabase
_mock_availability = {}
_mock_bookings = {}


async def get_available_slots(
    client_id: str,
    date: str = None,
    days_ahead: int = 7
) -> List[Dict]:
    """
    Returns available time slots for booking.

    :param client_id: The broker's client ID
    :param date: Specific date (YYYY-MM-DD) or None for next N days
    :param days_ahead: Number of days to check ahead
    :return: List of available slots
    """
    available_slots = []

    if date:
        # Check specific date
        slots = await _get_slots_for_date(client_id, date)
        available_slots.extend(slots)
    else:
        # Check next N days
        today = datetime.now().date()
        for i in range(1, days_ahead + 1):
            check_date = today + timedelta(days=i)
            date_str = check_date.strftime("%Y-%m-%d")

            # Skip Sundays (typical real estate off day)
            if check_date.weekday() != 6:
                slots = await _get_slots_for_date(client_id, date_str)
                available_slots.extend(slots)

    return available_slots


async def _get_slots_for_date(client_id: str, date: str) -> List[Dict]:
    """
    Gets available slots for a specific date, respecting custom availability from Supabase.
    Merges default business hours with broker's custom availability settings.
    """
    # Start with default business hours
    slots = _generate_default_slots(date)

    if supabase_client:
        try:
            # Check if broker has custom availability for this date
            custom_avail = supabase_client.table("availability")\
                .select("time, status")\
                .eq("client_id", client_id)\
                .eq("date", date)\
                .execute()

            if custom_avail.data:
                custom_map = {item["time"]: item["status"] for item in custom_avail.data}

                # Override default slots with custom availability
                for slot in slots:
                    time = slot["time"]
                    if time in custom_map:
                        slot["status"] = custom_map[time]

                # Also include custom slots added by the broker outside standard hours
                default_times = {s["time"] for s in slots}
                for custom_time, custom_status in custom_map.items():
                    if custom_time not in default_times and custom_status == "AVAILABLE":
                        slots.append({
                            "date": date,
                            "time": custom_time,
                            "status": "AVAILABLE"
                        })

            # Filter out BLOCKED and UNAVAILABLE slots
            slots = [s for s in slots if s["status"] == "AVAILABLE"]

            # Filter out already booked slots
            booked_times = supabase_client.table("bookings")\
                .select("time")\
                .eq("client_id", client_id)\
                .eq("date", date)\
                .eq("status", "CONFIRMED")\
                .execute()

            if booked_times.data:
                booked_set = {b["time"] for b in booked_times.data}
                slots = [s for s in slots if s["time"] not in booked_set]

        except Exception as e:
            logger.warning(f"Error fetching availability from Supabase, using defaults: {e}")

    # In-memory fallback: filter by bookings
    if not supabase_client:
        slots = [s for s in slots if not _is_slot_booked(client_id, date, s["time"])]

    return slots


def _generate_default_slots(date: str) -> List[Dict]:
    """
    Generates default business hours time slots for a given date.
    Default: 10am-6pm, hourly slots
    """
    slots = []
    time_options = [
        "10:00 AM", "11:00 AM", "12:00 PM",
        "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM", "06:00 PM"
    ]

    for time in time_options:
        slots.append({
            "date": date,
            "time": time,
            "status": "AVAILABLE"
        })

    return slots


def _is_slot_booked(client_id: str, date: str, time: str) -> bool:
    """Check if a specific slot is already booked (in-memory fallback only)."""
    key = f"{client_id}:{date}:{time}"
    return key in _mock_bookings


async def book_slot(
    client_id: str,
    customer_phone: str,
    customer_name: str,
    date: str,
    time: str,
    property_info: str = None
) -> Dict:
    """
    Books a time slot for a site visit.

    :param client_id: Broker's client ID
    :param customer_phone: Customer's phone number
    :param customer_name: Customer's name
    :param date: Date (YYYY-MM-DD)
    :param time: Time (HH:MM AM/PM)
    :param property_info: Optional property details
    :return: Booking confirmation or error
    """
    # Check if slot is still available
    if _is_slot_booked(client_id, date, time):
        return {
            "status": "error",
            "message": "This slot is no longer available",
            "booked": False
        }

    # Create booking
    booking = {
        "client_id": client_id,
        "customer_phone": customer_phone,
        "customer_name": customer_name,
        "date": date,
        "time": time,
        "property_info": property_info,
        "status": "CONFIRMED"
    }

    if supabase_client:
        try:
            result = supabase_client.table("bookings").insert(booking).execute()
            if result.data:
                booked = result.data[0]
                logger.info(f"Booking created in Supabase: {customer_name} on {date} at {time}")
                return {
                    "status": "success",
                    "message": f"Booking confirmed for {date} at {time}",
                    "booked": True,
                    "booking_id": booked["id"],
                    "booking": booked
                }
        except Exception as e:
            logger.error(f"Supabase booking error: {e}")
            return {
                "status": "error",
                "message": f"Failed to create booking: {str(e)}",
                "booked": False
            }

    # In-memory fallback
    booking_id = str(uuid.uuid4())
    booking["id"] = booking_id
    booking["created_at"] = datetime.utcnow().isoformat()
    key = f"{client_id}:{date}:{time}"
    _mock_bookings[key] = booking

    logger.info(f"Booking created (in-memory): {customer_name} on {date} at {time}")

    return {
        "status": "success",
        "message": f"Booking confirmed for {date} at {time}",
        "booked": True,
        "booking_id": booking_id,
        "booking": booking
    }


async def get_client_bookings(
    client_id: str,
    start_date: str = None,
    end_date: str = None
) -> List[Dict]:
    """
    Returns all bookings for a client within date range.
    Used for CRM calendar view.
    """
    if supabase_client:
        try:
            query = supabase_client.table("bookings")\
                .select("*")\
                .eq("client_id", client_id)\
                .order("date", desc=False)\
                .order("time", desc=False)

            if start_date:
                query = query.gte("date", start_date)
            if end_date:
                query = query.lte("date", end_date)

            result = query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Error fetching bookings from Supabase: {e}")

    # In-memory fallback
    bookings = [
        booking for key, booking in _mock_bookings.items()
        if booking["client_id"] == client_id
    ]

    # Filter by date range if provided
    if start_date:
        bookings = [b for b in bookings if b["date"] >= start_date]
    if end_date:
        bookings = [b for b in bookings if b["date"] <= end_date]

    # Sort by date and time
    bookings.sort(key=lambda x: (x["date"], x["time"]))

    return bookings


async def cancel_booking(booking_id: str) -> Dict:
    """Cancels a booking and frees up the slot."""
    if supabase_client:
        try:
            result = supabase_client.table("bookings")\
                .update({"status": "CANCELLED"})\
                .eq("id", booking_id)\
                .execute()

            if result.data:
                logger.info(f"Booking {booking_id} cancelled in Supabase")
                return {"status": "success", "message": "Booking cancelled"}
        except Exception as e:
            logger.error(f"Error cancelling booking: {e}")
            return {"status": "error", "message": str(e)}

    # In-memory fallback
    for key, booking in _mock_bookings.items():
        if booking["id"] == booking_id:
            del _mock_bookings[key]
            logger.info(f"Booking {booking_id} cancelled (in-memory)")
            return {"status": "success", "message": "Booking cancelled"}

    return {"status": "error", "message": "Booking not found"}


async def update_availability(
    client_id: str,
    date: str,
    time: str,
    status: str  # "AVAILABLE" | "BLOCKED" | "UNAVAILABLE"
) -> Dict:
    """
    Allows broker to update their availability calendar.
    Used when broker wants to block off times or add custom slots.
    """
    availability_record = {
        "client_id": client_id,
        "date": date,
        "time": time,
        "status": status
    }

    if supabase_client:
        try:
            # Upsert: insert or update if exists
            result = supabase_client.table("availability")\
                .upsert(availability_record, on_conflict="client_id,date,time")\
                .execute()

            if result.data:
                logger.info(f"Availability updated in Supabase: {date} {time} -> {status}")
                return {
                    "status": "success",
                    "message": f"Availability updated for {date} at {time}"
                }
        except Exception as e:
            logger.error(f"Error updating availability: {e}")
            return {"status": "error", "message": str(e)}

    # In-memory fallback
    key = f"{client_id}:{date}:{time}"
    availability_record["updated_at"] = datetime.utcnow().isoformat()
    _mock_availability[key] = availability_record

    logger.info(f"Availability updated (in-memory): {date} {time} -> {status}")

    return {
        "status": "success",
        "message": f"Availability updated for {date} at {time}"
    }


def format_available_slots_for_ai(slots: List[Dict]) -> str:
    """
    Formats available slots into a readable string for AI to present to customers.
    Groups by date for better readability.
    """
    if not slots:
        return "No available slots in the next 7 days."

    # Group by date
    grouped = {}
    for slot in slots[:10]:  # Limit to 10 slots to avoid overwhelming customer
        date = slot["date"]
        if date not in grouped:
            grouped[date] = []
        grouped[date].append(slot["time"])

    # Format message
    lines = []
    for date, times in grouped.items():
        # Convert date to readable format (e.g., "Monday, Nov 15")
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %b %d")

        times_str = ", ".join(times)
        lines.append(f"• {formatted_date}: {times_str}")

    return "\n".join(lines)
