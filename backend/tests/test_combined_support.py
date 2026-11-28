from handework.extensions import db
from handework.models import AuditLog, Role, User


def test_support_queue_restricted_and_audited(client, customer, artisan):
    result = client.post('/v1/support', json={'email':'help@example.com','topic':'general','message':'Please help'})
    assert result.status_code == 201
    ticket_id = result.get_json()['id']
    assert client.get('/v1/admin/support', headers=customer['headers']).status_code == 403
    user = db.session.get(User, artisan['user']['id'])
    user.role = Role.ADMIN
    db.session.commit()
    login = client.post('/v1/auth/login', json={'email':'kojo@example.com','password':'StrongPass123'})
    assert login.status_code == 200
    headers = {'Authorization':'Bearer '+login.get_json()['access_token']}
    assert client.get('/v1/admin/support', headers=headers).status_code == 200
    url = '/v1/admin/support/'+ticket_id
    assert client.patch(url,headers=headers,json={'status':'resolved'}).status_code == 422
    result = client.patch(url,headers=headers,json={'status':'resolved','reason':'Issue addressed'})
    assert result.status_code == 200
    assert result.get_json()['status'] == 'resolved'
    assert AuditLog.query.filter_by(action='support.status', entity_id=ticket_id).count() == 1
    assert client.get('/v1/admin/support?status=resolved',headers=headers).get_json()['items'][0]['id'] == ticket_id
