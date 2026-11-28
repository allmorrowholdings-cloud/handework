from handework.models import ArtisanProfile, User


def payload():
    return dict(first_name='Esi', last_name='Test', email='onboarding@example.com',
                phone='0244000008', password='StrongPass123', trade='Software architect',
                secondary_services='Software architecture', city='Accra', area='Osu',
                radius_km=25, years_experience=5, latitude=5.55, longitude=-0.18)


def test_registration_persists_location_and_capabilities(client, app):
    response = client.post('/v1/auth/register-artisan', json=payload())
    assert response.status_code == 201
    with app.app_context():
        profile = ArtisanProfile.query.filter_by(user_id=response.json['user']['id']).one()
        assert float(profile.latitude) == 5.55
        assert float(profile.longitude) == -0.18
        assert profile.secondary_services == 'Software architecture'
        assert not profile.available
        assert profile.verification_status != 'approved'


def test_invalid_location_rolls_back_registration(client, app):
    response = client.post('/v1/auth/register-artisan', json={**payload(), 'longitude': None})
    assert response.status_code == 422
    with app.app_context():
        assert User.query.filter_by(email=payload()['email']).first() is None
