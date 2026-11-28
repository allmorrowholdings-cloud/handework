from handework.services.service_catalogue import CATALOGUE, specific_service, capability_matches


def test_catalogue_size_and_identifiers():
    assert len(CATALOGUE) == 219
    assert len({r['category'] for r in CATALOGUE}) == 35
    assert len({r['id'] for r in CATALOGUE}) == len(CATALOGUE)
    assert all(len(r['name']) <= 120 for r in CATALOGUE)


def test_explicit_capability_required():
    service = specific_service('CCTV installation')
    assert service == specific_service('security camera installation')
    assert not capability_matches(service, 'Electrician', '')
    assert not capability_matches(service, 'Electrician', 'CCTV installation training')
    assert capability_matches(service, 'Electrician', 'Lighting installation, CCTV installation')
    assert not capability_matches(service, 'Electrician', 'CCTV repair')
    assert specific_service('Plumbing') is None


def test_service_directory_and_specific_search(client, artisan):
    assert len(client.get('/v1/services').json['catalogue']) == 219
    url = '/v1/artisans/search?service=CCTV+installation&coordinates=5.56,-0.18'
    assert client.get(url).json['items'] == []
    result = client.patch('/v1/artisans/me', json={'secondary_services':'CCTV installation'}, headers=artisan['headers'])
    assert result.status_code == 200
    assert result.json['artisan']['secondary_services'] == 'CCTV installation'
    assert client.get(url).json['items'][0]['id'] == artisan['profile_id']


def test_building_and_software_architecture_are_distinct():
    building = specific_service('Architect')
    software = specific_service('Software architect')
    assert building == specific_service('Architectural design')
    assert software == specific_service('Application architect')
    assert building and software and building != software
    assert capability_matches(building, 'Architect', '')
    assert not capability_matches(building, 'Software architect', '')
    assert not capability_matches(software, 'Architect', '')
    assert capability_matches(software, 'Application architect', '')


def test_architecture_search_uses_declared_discipline(client, artisan):
    url = '/v1/artisans/search'
    headers = artisan['headers']
    profile_id = artisan['profile_id']
    assert client.patch('/v1/artisans/me', json={'trade':'Architect', 'secondary_services':''}, headers=headers).status_code == 200
    for service in ('Architect', 'Architectural design'):
        result = client.get(url, query_string={'service':service, 'coordinates':'5.56,-0.18'}).json['items']
        assert profile_id in [r['id'] for r in result]
    assert client.get(url, query_string={'service':'Software architecture'}).json['items'] == []
    assert client.patch('/v1/artisans/me', json={'trade':'Software architect', 'secondary_services':''}, headers=headers).status_code == 200
    assert client.get(url, query_string={'service':'Architect'}).json['items'] == []
    assert profile_id in [r['id'] for r in client.get(url, query_string={'service':'Application architect'}).json['items']]
