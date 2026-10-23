"""Two independent native boundaries against exact sealed app methods."""
from tests.test_security import auth_client, register  # noqa: F401


def test_private_validation_refusal_keeps_body_and_no_store(auth_client):
    client, _ = auth_client
    register(client, 'independent-validation')
    response = client.post('/api/profiles', content='{', headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert response.json()['detail']
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'


def test_moderator_id_is_exact_and_an_email_or_suffixed_id_never_grants(auth_client):
    client, settings = auth_client
    principal = register(client, 'independent-moderator')
    settings.moderator_emails = principal['email']
    settings.moderator_user_ids = principal['email'] + ',' + principal['user_id'] + '-suffix'
    assert client.get('/api/social/moderation/reports').status_code == 403
    settings.moderator_user_ids = ' , ' + principal['user_id'] + ', , '
    response = client.get('/api/social/moderation/reports')
    assert response.status_code == 200 and response.json()['items'] == []
    settings.moderator_user_ids = ''
    assert client.get('/api/social/moderation/reports').status_code == 403
