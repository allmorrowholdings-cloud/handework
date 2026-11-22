from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models import (ArtisanProfile, AuditLog, Booking, BookingStatus, Dispute, Payment, PaymentStatus, RiskEvent, Role, SupportTicket, Verification, WorkProofEvidence)
from ..security import current_user, role_required
from ..services.storage import private_download_url
from ..services.notifications import dispatch_notifications, queue_notifications

bp = Blueprint("admin", __name__)


@bp.get("/admin/queue")
@role_required(Role.ADMIN)
def operations_queue():
    items=[]
    for row in Verification.query.filter_by(status="pending").order_by(Verification.created_at).limit(50): items.append({"id":row.id,"kind":"verification","title":row.kind,"status":row.status,"created_at":row.created_at.isoformat()})
    for row in WorkProofEvidence.query.filter_by(status="pending").order_by(WorkProofEvidence.created_at).limit(50): items.append({"id":row.id,"kind":"workproof","title":row.title,"status":row.status,"created_at":row.created_at.isoformat()})
    for row in Dispute.query.filter_by(status="open").order_by(Dispute.created_at).limit(50): items.append({"id":row.id,"kind":"dispute","title":row.reason,"status":row.status,"created_at":row.created_at.isoformat()})
    for row in SupportTicket.query.filter_by(status="open").order_by(SupportTicket.created_at).limit(50): items.append({"id":row.id,"kind":"support","title":row.topic,"status":row.status,"created_at":row.created_at.isoformat()})
    for row in RiskEvent.query.filter_by(decision="review").order_by(RiskEvent.score.desc()).limit(50): items.append({"id":row.id,"kind":"risk","title":row.kind,"status":row.decision,"score":row.score,"created_at":row.created_at.isoformat()})
    items.sort(key=lambda x:x["created_at"]);return jsonify({"items":items[:100]})


@bp.get("/admin/verifications")
@role_required(Role.ADMIN)
def verification_queue():
    status=request.args.get("status","pending");rows=Verification.query.filter_by(status=status).order_by(Verification.created_at).limit(200).all();return jsonify({"items":[{"id":x.id,"artisan_id":x.artisan_id,"kind":x.kind,"file_url":private_download_url(x.file_url),"payout_name":x.provider_reference if x.kind=="payout_name" else None,"status":x.status,"created_at":x.created_at.isoformat()} for x in rows]})


@bp.post("/admin/verifications/<verification_id>/decision")
@role_required(Role.ADMIN)
def verification_decision(verification_id):
    admin=current_user();row=Verification.query.get_or_404(verification_id);data=request.get_json(silent=True) or {};decision=str(data.get("decision") or "")
    if decision not in ("approved","rejected","replacement_required"):return jsonify({"message":"Invalid decision"}),422
    before={"status":row.status};row.status,row.reviewer_id,row.decision_reason,row.decided_at=decision,admin.id,str(data.get("reason") or "")[:500],datetime.now(timezone.utc)
    profile=ArtisanProfile.query.get(row.artisan_id);required={"government_id","live_selfie","trade_proof","payout_name"};approved={x.kind for x in Verification.query.filter_by(artisan_id=profile.id,status="approved").all()}
    if decision=="approved":approved.add(row.kind)
    if required.issubset(approved):profile.verification_status="approved"
    elif decision=="rejected":profile.verification_status="rejected"
    db.session.add(AuditLog(actor_id=admin.id,action="verification.decision",entity_type="verification",entity_id=row.id,before=before,after={"status":decision,"reason":row.decision_reason}));notification_ids=queue_notifications(profile.user,"Verification updated",f"{row.kind.replace('_',' ')} is {decision.replace('_',' ')}.",{"verification_id":row.id},urgent=decision in ("rejected","replacement_required"));db.session.commit();dispatch_notifications(notification_ids);return jsonify({"status":row.status,"profile_status":profile.verification_status})


@bp.get("/admin/disputes")
@role_required(Role.ADMIN)
def dispute_queue():
    rows=Dispute.query.order_by(Dispute.created_at).limit(200).all();return jsonify({"items":[{"id":x.id,"booking_id":x.booking_id,"reason":x.reason,"description":x.description,"status":x.status,"created_at":x.created_at.isoformat()} for x in rows]})


@bp.post("/admin/disputes/<dispute_id>/decision")
@role_required(Role.ADMIN)
def dispute_decision(dispute_id):
    admin=current_user();row=Dispute.query.with_for_update().get_or_404(dispute_id);data=request.get_json(silent=True) or {};decision=str(data.get("decision") or "")
    if decision not in ("release_to_artisan","refund_customer","split","no_action"):return jsonify({"message":"Invalid dispute decision"}),422
    row.status,row.resolution,row.resolved_at,row.assigned_admin_id="resolved",str(data.get("resolution") or "")[:4000],datetime.now(timezone.utc),admin.id
    db.session.add(AuditLog(actor_id=admin.id,action="dispute.decision",entity_type="dispute",entity_id=row.id,before={"status":"open"},after={"status":"resolved","decision":decision,"resolution":row.resolution}));db.session.commit()
    return jsonify({"status":row.status,"financial_action":decision,"message":"Use the signed release or refund endpoint to move funds; the dispute record does not change the ledger by itself."})


@bp.get("/admin/payments")
@role_required(Role.ADMIN)
def payment_exceptions():
    statuses=[PaymentStatus.PENDING,PaymentStatus.FAILED,PaymentStatus.REFUND_PENDING];rows=Payment.query.filter(Payment.status.in_(statuses)).order_by(Payment.created_at).limit(200).all();return jsonify({"items":[{"id":x.id,"booking_id":x.booking_id,"reference":x.provider_reference,"amount":float(x.amount),"currency":x.currency,"status":x.status.value,"created_at":x.created_at.isoformat()} for x in rows]})


@bp.get("/admin/risk")
@role_required(Role.ADMIN)
def risk_queue():
    rows=RiskEvent.query.filter(RiskEvent.decision.in_(["review","block"])).order_by(RiskEvent.score.desc(),RiskEvent.created_at).limit(200).all();return jsonify({"items":[{"id":x.id,"user_id":x.user_id,"booking_id":x.booking_id,"payment_id":x.payment_id,"kind":x.kind,"score":x.score,"signals":x.signals,"decision":x.decision,"created_at":x.created_at.isoformat()} for x in rows]})


@bp.post("/admin/risk/<event_id>/decision")
@role_required(Role.ADMIN)
def risk_decision(event_id):
    admin=current_user();row=RiskEvent.query.get_or_404(event_id);decision=str((request.get_json(silent=True) or {}).get("decision") or "")
    if decision not in ("allow","block","monitor"):return jsonify({"message":"Invalid decision"}),422
    before=row.decision;row.decision=decision;db.session.add(AuditLog(actor_id=admin.id,action="risk.decision",entity_type="risk_event",entity_id=row.id,before={"decision":before},after={"decision":decision}));db.session.commit();return jsonify({"decision":row.decision})


@bp.get("/admin/analytics")
@role_required(Role.ADMIN)
def analytics():
    since=datetime.now(timezone.utc)-timedelta(days=min(max(int(request.args.get("days",30)),1),365));metrics={"period_days":(datetime.now(timezone.utc)-since).days,"bookings":Booking.query.filter(Booking.created_at>=since).count(),"completed_bookings":Booking.query.filter(Booking.completed_at>=since,Booking.status==BookingStatus.COMPLETED).count(),"gross_payment_value":float(db.session.query(db.func.coalesce(db.func.sum(Payment.amount),0)).filter(Payment.paid_at>=since).scalar()),"currency":"GHS","open_disputes":Dispute.query.filter_by(status="open").count(),"pending_verifications":Verification.query.filter_by(status="pending").count()};metrics["items"]=[{"id":key,"title":key.replace("_"," ").title(),"status":f"{value} {metrics['currency']}" if key=="gross_payment_value" else str(value)} for key,value in metrics.items() if key not in ("currency","items")];return jsonify(metrics)
