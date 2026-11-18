"""
ARVANA HOT Lead Alert System - Feature 5
Sends instant WhatsApp alerts to brokers when HOT leads are identified.
"""

import logging
from lib import whatsapp

logger = logging.getLogger("arvana.notifications")


async def send_hot_lead_alert(
    broker_phone: str,
    lead_data: dict,
    client_config: dict
) -> dict:
    """
    Feature 5: Sends instant WhatsApp alert to broker when a HOT lead is identified.

    :param broker_phone: Broker's WhatsApp number (from client config)
    :param lead_data: Extracted lead data with classification
    :param client_config: Client configuration (for phone_number_id and access_token)
    :return: Alert delivery status
    """

    classification = lead_data.get("classification", "NEW")

    # Only send alert for HOT leads
    if classification != "HOT":
        return {"status": "not_hot_lead", "classification": classification}

    # Build alert message
    customer_phone = lead_data.get("customer_phone", "Unknown")
    name = lead_data.get("name") or "New Lead"
    budget = lead_data.get("budget_range") or lead_data.get("budget") or "Not disclosed"
    timeline = lead_data.get("timeline") or "Not disclosed"
    summary = lead_data.get("ai_summary", "No summary available")

    alert_message = f"""🔥 *HOT LEAD ALERT* 🔥

Name: {name}
Phone: {customer_phone}
Budget: {budget}
Timeline: {timeline}

Summary:
{summary}

ACTION REQUIRED: This lead is ready to convert. Call them NOW!"""

    # Send alert to broker's WhatsApp
    try:
        result = await whatsapp.send_whatsapp_text(
            to_phone=broker_phone,
            text=alert_message,
            phone_number_id=client_config.get("phone_number_id"),
            access_token=client_config.get("access_token")
        )

        logger.info(f"HOT lead alert sent to broker {broker_phone} for lead {customer_phone}")
        return {"status": "alert_sent", "to": broker_phone, "result": result}

    except Exception as e:
        logger.error(f"Failed to send HOT lead alert: {e}")
        return {"status": "alert_failed", "error": str(e)}


async def send_site_visit_booking_confirmation(
    broker_phone: str,
    customer_phone: str,
    booking_details: dict,
    client_config: dict
) -> dict:
    """
    Feature 2: Notifies broker when a customer books a site visit.

    :param broker_phone: Broker's WhatsApp number
    :param customer_phone: Customer's phone number
    :param booking_details: Dictionary with date, time, location
    :param client_config: Client configuration
    :return: Notification delivery status
    """

    date = booking_details.get("date", "Not specified")
    time = booking_details.get("time", "Not specified")
    location = booking_details.get("location", "Not specified")
    customer_name = booking_details.get("customer_name", "Customer")

    notification = f"""📅 *SITE VISIT BOOKING REQUEST*

Customer: {customer_name}
Phone: {customer_phone}
Requested Date: {date}
Requested Time: {time}
Location: {location}

ACTION: Please confirm this booking with the customer."""

    try:
        result = await whatsapp.send_whatsapp_text(
            to_phone=broker_phone,
            text=notification,
            phone_number_id=client_config.get("phone_number_id"),
            access_token=client_config.get("access_token")
        )

        logger.info(f"Site visit booking notification sent to broker {broker_phone}")
        return {"status": "notification_sent", "to": broker_phone, "result": result}

    except Exception as e:
        logger.error(f"Failed to send booking notification: {e}")
        return {"status": "notification_failed", "error": str(e)}
