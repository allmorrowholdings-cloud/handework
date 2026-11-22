from datetime import datetime, timezone
from ..extensions import db
from ..models import (ArtisanProfile, Booking, BookingStatus, Dispute, Review,
                      Verification, WorkProofEvidence, WorkProofProfile)


def recalculate_workproof(artisan):
    completed = Booking.query.filter_by(artisan_id=artisan.id, status=BookingStatus.COMPLETED).all()
    external = WorkProofEvidence.query.filter_by(artisan_id=artisan.id, evidence_type="external_job", status="verified").all()
    verified_jobs = len(completed) + len(external)
    all_jobs = Booking.query.filter(Booking.artisan_id == artisan.id, Booking.status.in_([BookingStatus.COMPLETED, BookingStatus.CANCELLED, BookingStatus.DISPUTED])).count()
    completion_rate = (len(completed) / all_jobs * 100) if all_jobs else 0
    reviews = Review.query.filter_by(artisan_id=artisan.id, moderation_status="published").all()
    rating = sum(row.rating for row in reviews) / len(reviews) if reviews else None
    client_counts = {}
    for row in completed: client_counts[row.customer_id] = client_counts.get(row.customer_id, 0) + 1
    repeat_clients = sum(1 for count in client_counts.values() if count > 1)
    unresolved = Dispute.query.join(Booking, Dispute.booking_id == Booking.id).filter(Booking.artisan_id == artisan.id, Dispute.status != "resolved").count()
    dates = [row.completed_at or row.created_at for row in completed] + [row.occurred_at or row.created_at for row in external]
    first_activity = min(dates) if dates else None
    if first_activity and first_activity.tzinfo is None: first_activity = first_activity.replace(tzinfo=timezone.utc)
    years_verified = ((datetime.now(timezone.utc) - first_activity).days / 365.25) if first_activity else 0
    identity = Verification.query.filter_by(artisan_id=artisan.id, kind="government_id", status="approved").first() is not None
    score = min(1000, round(
        min(verified_jobs, 300) * 1.4 + completion_rate * 2.2 +
        ((rating or 0) / 5) * 170 + min(repeat_clients, 100) * 1.1 +
        min(years_verified, 10) * 8 + (60 if identity else 0) - min(unresolved, 5) * 45
    ))
    row = WorkProofProfile.query.filter_by(artisan_id=artisan.id).first() or WorkProofProfile(artisan_id=artisan.id)
    row.score, row.verified_jobs, row.external_verified_jobs = max(score, 0), verified_jobs, len(external)
    row.repeat_clients, row.completion_rate, row.average_rating = repeat_clients, completion_rate, rating
    row.unresolved_disputes, row.years_verified, row.last_calculated_at = unresolved, years_verified, datetime.now(timezone.utc)
    db.session.add(row)
    return row, identity


def public_workproof(artisan):
    row, identity = recalculate_workproof(artisan)
    db.session.commit()
    evidence = WorkProofEvidence.query.filter_by(artisan_id=artisan.id, status="verified").order_by(WorkProofEvidence.occurred_at.desc()).limit(50).all()
    return {"score": row.score, "verified_jobs": row.verified_jobs, "external_verified_jobs": row.external_verified_jobs,
            "completion_rate": float(row.completion_rate), "average_rating": float(row.average_rating) if row.average_rating is not None else None,
            "repeat_clients": row.repeat_clients, "years_verified": float(row.years_verified), "unresolved_disputes": row.unresolved_disputes,
            "identity_verified": identity, "evidence": [{"id": item.id, "type": item.evidence_type, "title": item.title,
            "occurred_at": item.occurred_at.isoformat() if item.occurred_at else None, "details": item.public_metadata or {}} for item in evidence],
            "methodology": "Score uses verified jobs, completion, client ratings, repeat clients, verified activity, identity and unresolved disputes.",
            "disclaimer": "WorkProof is a work-reputation indicator, not a credit score or guarantee."}
