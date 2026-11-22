import os
from handework import create_app
from handework.extensions import db
from handework.models import Role, User

app=create_app()
with app.app_context():
    email=os.environ["ADMIN_EMAIL"].strip().lower();password=os.environ["ADMIN_PASSWORD"];phone=os.environ["ADMIN_PHONE"]
    user=User.query.filter_by(email=email).first()
    if not user:
        user=User(email=email,phone=phone,first_name=os.getenv("ADMIN_FIRST_NAME","handEwork"),last_name=os.getenv("ADMIN_LAST_NAME","Admin"),role=Role.ADMIN);user.set_password(password);db.session.add(user)
    else:user.role=Role.ADMIN;user.set_password(password)
    db.session.commit();print("Admin account ready")
