"""Shared booking eligibility checks; no payment or verification state mutations."""
from datetime import time
from ..models import Availability
from .distance import haversine_km
from .service_catalogue import specific_service, capability_matches


def readiness(profile):
    checks = {
        "active_account": profile.user.status == "active",
        "approved": profile.verification_status == "approved",
        "declared_service": bool((profile.trade or "").strip() or (profile.secondary_services or "").strip()),
        "located": profile.latitude is not None and profile.longitude is not None and 1 <= profile.radius_km <= 100,
        "accepting_work": bool(profile.available),
    }
    return {**checks, "ready": all(checks.values()), "missing": [key for key, value in checks.items() if not value]}


def parse_start(value):
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        raise ValueError("Use HH:MM for a working time")
    if not (value[:2].isdigit() and value[3:].isdigit()):
        raise ValueError("Use HH:MM for a working time")
    return time(int(value[:2]), int(value[3:]))


def within_slot(slot, start):
    return bool(slot and slot.active and slot.start_time <= start < slot.end_time)


def booking_blocker(profile, service, coordinates=None, scheduled=None, require_hours=False):
    if profile.user.status != "active" or profile.verification_status != "approved":
        return "This professional is not eligible to accept work."
    if not profile.available or not 1 <= profile.radius_km <= 100:
        return "This professional is not accepting work."
    specific = specific_service(service)
    if specific and not capability_matches(specific, profile.trade, profile.secondary_services):
        return "This professional has not listed the requested service."
    if coordinates is not None:
        if profile.latitude is None or profile.longitude is None:
            return "This professional has not configured a service location."
        if haversine_km(*coordinates, profile.latitude, profile.longitude) > profile.radius_km:
            return "The job is outside this professional's service radius."
    if scheduled is not None:
        slots = Availability.query.filter_by(artisan_id=profile.id).all()
        # Legacy professionals without saved hours remain eligible for quote requests only.
        if require_hours or slots:
            slot = next((row for row in slots if row.weekday == scheduled.weekday()), None)
            if not within_slot(slot, scheduled.time()):
                return "This professional is not working at the selected time."
    return None


def booking_coordinates(booking):
    if booking.latitude is None or booking.longitude is None:
        return None
    return booking.latitude, booking.longitude
