from handework.extensions import db
def test_health(client):
    response=client.get("/v1/health")
    assert response.status_code==200
    assert response.get_json()["database"]=="ok"


def test_registration_and_login(client):
    payload={"first_name":"Esi","last_name":"Mensah","email":"esi@example.com","phone":"0244000003","password":"StrongPass123"}
    created=client.post("/v1/auth/register",json=payload)
    assert created.status_code==201
    logged_in=client.post("/v1/auth/login",json={"email":payload["email"],"password":payload["password"]})
    assert logged_in.status_code==200
    assert logged_in.get_json()["user"]["role"]=="customer"


def test_rejects_duplicate_account(client,customer):
    response=client.post("/v1/auth/register",json={"first_name":"Ama","last_name":"Again","email":"ama@example.com","phone":"0244000004","password":"StrongPass123"})
    assert response.status_code==409


def test_account_settings_are_persisted(client,customer):
    response=client.patch("/v1/auth/me",json={"first_name":"Akosua","notification_preferences":{"push":False,"whatsapp":True,"sms":True}},headers=customer["headers"])
    assert response.status_code==200
    body=response.get_json()["user"]
    assert body["first_name"]=="Akosua"
    assert body["notification_preferences"]["whatsapp"] is True


def test_public_support_ticket_is_saved(client, app):
    from handework.models import SupportTicket
    response = client.post("/v1/support", json={"topic":"safety","email":"person@example.com","message":"Please contact me"})
    assert response.status_code == 201
    with app.app_context():
        ticket = db.session.get(SupportTicket, response.get_json()["id"])
        assert ticket.email == "person@example.com"
        assert ticket.priority == "urgent"


def test_support_rejects_an_unknown_booking_reference(client):
    response = client.post("/v1/support", json={"topic":"booking","email":"person@example.com","message":"Please help","booking_id":"missing"})
    assert response.status_code == 404
