from datetime import datetime, timezone
from flask import Blueprint, current_app, jsonify, request
from ..services.email_delivery import queue_email
from ..extensions import db
from ..models import ArtisanProfile, AuditLog, FileAsset, Role, WorkProofEvidence
from ..security import current_user, role_required
from ..services.storage import upload_file, metadata_for, private_download_url, delete_object
from ..services.workproof import public_workproof

bp = Blueprint("workproof", __name__)


@bp.get("/workproof/<artisan_id>")
def public_record(artisan_id):
    profile = ArtisanProfile.query.filter_by(id=artisan_id, verification_status="approved").first_or_404()
    return jsonify({"artisan_id": profile.id, "display_name": profile.display_name, "trade": profile.trade, "workproof": public_workproof(profile)})


@bp.route("/workproof/me", methods=["GET", "POST"])
@role_required(Role.ARTISAN)
def my_record():
    profile = ArtisanProfile.query.filter_by(user_id=current_user().id).first_or_404()
    if request.method == "POST":
        data = request.form if request.form else (request.get_json(silent=True) or {})
        required = ("title", "verifier_name", "verifier_contact")
        if any(not str(data.get(key) or "").strip() for key in required):
            return jsonify({"message": "Title, verifier name and verifier contact are required"}), 422
        occurred_at = None
        if data.get("occurred_at"):
            try: occurred_at = datetime.fromisoformat(str(data["occurred_at"]).replace("Z", "+00:00"))
            except ValueError: return jsonify({"message": "occurred_at must be an ISO date"}), 422
        file = request.files.get("file")
        asset = None
        if file and file.filename:
            try:
                stored=upload_file(file,current_user().id,"workproof_evidence",private=True)
            except ValueError as error:
                db.session.rollback();return jsonify({"message":str(error)}),422
            except RuntimeError as error:
                db.session.rollback();return jsonify({"message":str(error)}),503
        try:
            if file and file.filename:
                asset=FileAsset(owner_id=current_user().id,purpose="workproof_evidence",**metadata_for(stored));db.session.add(asset);db.session.flush()
            row = WorkProofEvidence(artisan_id=profile.id, evidence_type="external_job", title=str(data["title"]).strip()[:180],
                description=str(data.get("description") or "").strip()[:4000], occurred_at=occurred_at,
                verifier_name=str(data["verifier_name"]).strip()[:160], verifier_contact=str(data["verifier_contact"]).strip()[:254],
                public_metadata={"skill": str(data.get("skill") or "").strip()[:120]},file_asset_id=asset.id if asset else None)
            db.session.add(row)
            db.session.commit()
        except Exception:
            db.session.rollback()
            if file and file.filename:
                try: delete_object(stored.url)
                except Exception: current_app.logger.exception("WorkProof upload transaction cleanup failed")
            raise
        return jsonify({"id": row.id, "status": row.status, "message": "Submitted for independent verification"}), 201
    result = public_workproof(profile)
    rows = WorkProofEvidence.query.filter_by(artisan_id=profile.id).order_by(WorkProofEvidence.created_at.desc()).all()
    result["submissions"] = [{"id": x.id, "type": x.evidence_type, "title": x.title, "status": x.status, "decision_reason": x.decision_reason, "evidence_url":private_download_url(db.session.get(FileAsset,x.file_asset_id).url,300) if x.file_asset_id and db.session.get(FileAsset,x.file_asset_id) else None, "created_at": x.created_at.isoformat()} for x in rows]
    return jsonify({"workproof": result})


@bp.post("/admin/workproof/<evidence_id>/decision")
@role_required(Role.ADMIN)
def decide_evidence(evidence_id):
    row = WorkProofEvidence.query.get_or_404(evidence_id); data = request.get_json(silent=True) or {}; decision = str(data.get("decision") or "")
    if decision not in ("verified", "rejected", "revoked"): return jsonify({"message": "Invalid decision"}), 422
    before = row.status; row.status, row.reviewer_id = decision, current_user().id
    row.decision_reason, row.decided_at = str(data.get("reason") or "")[:500], datetime.now(timezone.utc)
    db.session.add(AuditLog(actor_id=current_user().id, action="workproof.decision", entity_type="workproof_evidence", entity_id=row.id, before={"status": before}, after={"status": decision}))
    if before != decision:
        profile = db.session.get(ArtisanProfile, row.artisan_id)
        queue_email(profile.user, "WorkProof verification updated", f"Your WorkProof submission is {decision}.")
    db.session.commit(); return jsonify({"id": row.id, "status": row.status})


@bp.get("/admin/workproof")
@role_required(Role.ADMIN)
def review_queue():
    rows=WorkProofEvidence.query.order_by(WorkProofEvidence.created_at.desc()).limit(200).all()
    return jsonify({"items":[{"id":row.id,"artisan_id":row.artisan_id,"title":row.title,"status":row.status,"evidence_url":private_download_url(db.session.get(FileAsset,row.file_asset_id).url,300) if row.file_asset_id and db.session.get(FileAsset,row.file_asset_id) else None,"created_at":row.created_at.isoformat()} for row in rows]})
