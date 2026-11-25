from ..extensions import db
from ..models import JournalPosting
from .paystack import minor


def post(reference, event, debit, credit, amount, currency):
    units = minor(amount)
    if units < 0 or debit == credit:
        raise ValueError("Invalid journal movement")
    if units:
        db.session.add(JournalPosting(reference=reference, event=event, debit=debit,
                                      credit=credit, units=units, currency=currency))
