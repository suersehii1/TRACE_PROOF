"""PostgreSQL을 사용하는 API 통합 시험. 각 시험의 변경은 외부 트랜잭션으로 되돌린다."""
import hashlib
import json
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import engine, get_db

RAW = Path(os.getenv('RAW_DATA_DIR', '/raw-data'))


@pytest.fixture
def client():
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode='create_savepoint')
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()


def upload(client, name):
    raw = (RAW / f'{name}.json').read_bytes()
    response = client.post('/api/releases/upload', files={'file': (f'{name}.json', raw, 'application/json')})
    assert response.status_code == 200, response.text
    return response.json()['release']


def compare(client, name):
    before, after = upload(client, 'baseline'), upload(client, name)
    response = client.post('/api/validations', json={'baseline_id': before['id'], 'candidate_id': after['id'], 'profile_id': 'PROFILE-DEMO-V1'})
    assert response.status_code == 200, response.text
    return response.json()


def test_ingest_auth_and_idempotency_and_exact_raw(client):
    raw = (RAW / 'baseline.json').read_bytes()
    assert client.post('/api/device/releases', content=raw).status_code == 401
    headers = {'Authorization': 'Bearer ' + os.getenv('DEVICE_TOKEN', 'traceproof_device_demo_only')}
    response = client.post('/api/device/releases', content=raw, headers=headers)
    assert response.status_code == 200
    r = response.json()['release']
    assert r['sha256'] == hashlib.sha256(raw).hexdigest()
    assert client.post('/api/device/releases', content=raw, headers=headers).json()['reused']
    assert client.get(f"/api/releases/{r['id']}/raw").content == raw


def test_failed_validation_cannot_be_approved_and_hold_is_audited(client):
    v = compare(client, 'faulty')
    body = {'disposition': 'APPROVED', 'reviewer': '테스트 담당자', 'note': '오류가 남아 있는 경우'}
    assert client.post(f"/api/validations/{v['id']}/review", json=body).status_code == 409
    body['disposition'] = 'HOLD'
    response = client.post(f"/api/validations/{v['id']}/review", json=body)
    assert response.json()['review_status'] == 'HOLD'
    assert len(response.json()['reviews']) == 1


def test_healthy_review_report_and_csv(client):
    v = compare(client, 'healthy')
    body = {'disposition': 'APPROVED', 'reviewer': '품질 <script>', 'note': '근거 확인 <script>alert(1)</script>'}
    response = client.post(f"/api/validations/{v['id']}/review", json=body)
    assert response.status_code == 200
    assert response.json()['review_status'] == 'APPROVED'
    report = client.get(f"/api/validations/{v['id']}/report")
    assert report.status_code == 200
    assert '<script>alert(1)</script>' not in report.text
    assert '&lt;script&gt;' in report.text
    csv = client.get(f"/api/validations/{v['id']}/checks.csv")
    assert csv.status_code == 200
    assert 'VIBRATION' in csv.text


def test_bad_upload_and_same_release_are_rejected(client):
    assert client.post('/api/releases/upload', files={'file': ('bad.json', b'not json')}).status_code == 422
    r = upload(client, 'baseline')
    response = client.post('/api/validations', json={'baseline_id': r['id'], 'candidate_id': r['id'], 'profile_id': 'PROFILE-DEMO-V1'})
    assert response.status_code == 422
