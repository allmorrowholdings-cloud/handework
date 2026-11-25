from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import Course, DriveSubmission, Role, TrainingProvider, User, utcnow
from ..security import current_user, role_required
from ..services.drive_links import parse_drive_link
from ..services.notifications import dispatch_notifications, queue_notifications

bp = Blueprint("drive_submissions", __name__)
MEMBERS = (Role.CUSTOMER, Role.ARTISAN, Role.ADMIN)
PURPOSES = ("portfolio", "training_resource", "course_material", "supporting_document")


def reviewed_course_query():
    return Course.query.join(TrainingProvider, Course.provider_id == TrainingProvider.id).filter(
        Course.published.is_(True), TrainingProvider.verification_status == "approved")


def record(row):
    return {**row.link(), "owner_id": row.owner_id, "status": row.status, "version": row.version,
            "review_note": row.review_note, "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None}


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def same_version(row, value):
    return type(value) is int and row.version == value


@bp.route("/drive-submissions", methods=["GET", "POST"])
@role_required(*MEMBERS)
def submissions():
    user = current_user()
    if request.method == "GET":
        rows = DriveSubmission.query.filter_by(owner_id=user.id).order_by(DriveSubmission.created_at.desc())
        return jsonify(items=[record(row) for row in rows])
    data = body()
    purpose = data.get("purpose")
    if purpose not in PURPOSES:
        return jsonify(message="Unsupported purpose for an external link"), 422
    if purpose == "portfolio" and user.role != Role.ARTISAN:
        return jsonify(message="Portfolio submissions require an artisan account"), 403
    course_id = data.get("course_id")
    if purpose == "course_material":
        if not isinstance(course_id, str) or not reviewed_course_query().filter(Course.id == course_id).first():
            return jsonify(message="Choose a published course from an approved provider"), 422
    elif course_id is not None:
        return jsonify(message="Only course materials can be attached to a course"), 422
    title = data.get("title")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 180:
        return jsonify(message="Enter a title of up to 180 characters"), 422
    try:
        url, kind, key = parse_drive_link(data.get("url"))
    except ValueError as error:
        return jsonify(message=str(error)), 422
    row = DriveSubmission(owner_id=user.id, title=title.strip(), purpose=purpose, course_id=course_id,
                          url=url, drive_id=key, item_kind=kind)
    db.session.add(row)
    db.session.commit()
    return jsonify(item=record(row)), 201


@bp.route("/drive-submissions/<submission_id>", methods=["PUT", "DELETE"])
@role_required(*MEMBERS)
def change_submission(submission_id):
    row = DriveSubmission.query.filter_by(id=submission_id, owner_id=current_user().id).with_for_update().first_or_404()
    data = body()
    if not same_version(row, data.get("version")):
        return jsonify(message="This submission has changed. Refresh before continuing."), 409
    if request.method == "DELETE":
        db.session.delete(row)
        db.session.commit()
        return jsonify(removed=True)
    try:
        url, kind, key = parse_drive_link(data.get("url"))
    except ValueError as error:
        return jsonify(message=str(error)), 422
    row.url, row.item_kind, row.drive_id = url, kind, key
    row.status, row.review_note, row.reviewer_id, row.reviewed_at = "pending", None, None, None
    row.version += 1
    db.session.commit()
    return jsonify(item=record(row))


@bp.get("/admin/drive-submissions")
@role_required(Role.ADMIN)
def review_queue():
    status = request.args.get("status", "pending")
    if status not in ("pending", "approved", "rejected"):
        return jsonify(message="Unknown review status"), 422
    rows = db.session.query(DriveSubmission, User, Course.title).join(
        User, DriveSubmission.owner_id == User.id).outerjoin(Course, DriveSubmission.course_id == Course.id
    ).filter(DriveSubmission.status == status).order_by(DriveSubmission.created_at)
    return jsonify(items=[{**record(row), "owner_name": f"{owner.first_name} {owner.last_name}",
                           "course_title": title} for row, owner, title in rows])


@bp.post("/admin/drive-submissions/<submission_id>/review")
@role_required(Role.ADMIN)
def review(submission_id):
    data = body()
    decision = data.get("status")
    note = data.get("note", "")
    if decision not in ("approved", "rejected") or not isinstance(note, str) or len(note) > 500:
        return jsonify(message="Choose a review decision and use at most 500 characters for feedback"), 422
    row = DriveSubmission.query.filter_by(id=submission_id).with_for_update().first_or_404()
    if not same_version(row, data.get("version")) or row.status != "pending":
        return jsonify(message="Refresh the queue to review the current submission"), 409
    row.status, row.reviewer_id, row.reviewed_at = decision, current_user().id, utcnow()
    row.review_note = note.strip() or None
    row.version += 1
    ids = queue_notifications(db.session.get(User, row.owner_id), "Google Drive submission reviewed",
                              f"Your {row.purpose.replace('_', ' ')} link was {decision}. See your submissions for details.",
                              {"submission_id": row.id})
    db.session.commit()
    dispatch_notifications(ids)
    return jsonify(item=record(row))


@bp.get("/training/drive-resources")
def training_resources():
    links = DriveSubmission.query.filter_by(status="approved")
    rows = links.filter_by(purpose="training_resource").order_by(DriveSubmission.title)
    materials = db.session.query(DriveSubmission, Course.title).join(Course, DriveSubmission.course_id == Course.id
    ).join(TrainingProvider, Course.provider_id == TrainingProvider.id).filter(
        DriveSubmission.status == "approved", DriveSubmission.purpose == "course_material",
        Course.published.is_(True), TrainingProvider.verification_status == "approved").order_by(Course.title, DriveSubmission.title)
    return jsonify(items=[row.link() for row in rows] +
                   [{**row.link(), "course_title": title} for row, title in materials])
