"""P4/P5 SQL/API and P6 defensive adapter subcases, independent of author helpers."""
import asyncio
import json
import logging
import os
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.fetching import Fetcher, FetchResult
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.search.intent import DiscoveryIntent
from app.api.routes_research import router
from app.config import Settings
from app.db import get_session
from app.domain.enums import DegreeLevel, FetchOutcome
from app.jobs.store import JobStore
from app.jobs.worker import Worker
from app.models import ApplicantProfileRow, AuditEvent, ClaimRow, Job, Organization, ResearchRun
from app.models.base import Base
from app.pipeline.runner import ResearchRunner
from app.schemas.profile import ApplicantProfileIn, ApplicationContext
from app.security import Principal, get_principal


def record(name, data):
    target = Path(os.environ['OWN_OBSERVATIONS'])
    (target / (name + '.json')).write_text(json.dumps(data, default=str, indent=2) + '\n')


def profile():
    return ApplicantProfileIn(context=ApplicationContext(
        level='bachelor', intended_fields=['Mathematics'], intake_year=2027,
        citizenship='Kazakhstan', country_of_residence='Kazakhstan',
        education_country='Kazakhstan', education_system='Synthetic secondary',
    ))


def settings(tmp_path):
    return Settings(_env_file=None, demo_mode=True, enable_browser_tier=False,
                    search_provider='none', decision_provider='none',
                    cache_dir=tmp_path / 'cache', export_dir=tmp_path / 'exports')


def fixture_db(tmp_path):
    db = tmp_path / 'independent.sqlite'
    engine = create_engine('sqlite:///' + str(db), connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        org = Organization(name='Synthetic own workspace', slug='synthetic-peer')
        session.add(org)
        session.flush()
        p = profile()
        row = ApplicantProfileRow(organization_id=org.id, display_name='Synthetic peer',
                                  payload=p.model_dump(mode='json'))
        session.add(row)
        session.flush()
        run = ResearchRun(profile_id=row.id, demo_mode=True, stage='queued',
                          unknowns=['prior unresolved source'], errors=[], stage_state={})
        session.add(run)
        session.commit()
        identifiers = (org.id, row.id, run.id)
    return engine, factory, p, identifiers


def api_read(factory, organization_id, run_id):
    app = FastAPI()
    app.include_router(router)

    def own_session():
        with factory() as session:
            yield session

    owner = Principal(user_id='synthetic-user', organization_id=organization_id,
                      email='peer@example.invalid', display_name='Synthetic peer', role='owner')
    app.dependency_overrides[get_session] = own_session
    app.dependency_overrides[get_principal] = lambda: owner
    with TestClient(app) as client:
        response = client.get('/api/runs/' + run_id)
        assert response.status_code == 200
        payload = response.json()
        app.dependency_overrides[get_principal] = lambda: Principal(
            user_id='other-user', organization_id='0' * 32, email='other@example.invalid',
            display_name='Other synthetic', role='owner')
        denied = client.get('/api/runs/' + run_id)
        assert denied.status_code == 404
    return payload


def assert_absent(marker, payload):
    assert marker not in json.dumps(payload, default=str), 'raw synthetic sentinel retained in actual persisted/serialized diagnostics'


def test_p4_real_SQL_adapter_recorders_and_native_API(tmp_path):
    marker = 'A_SQL_ADAPTER_UNIQUE'
    poisoned = 'https://public.invalid/cost?token=' + marker
    engine, factory, p, (org_id, _, run_id) = fixture_db(tmp_path)
    try:
        async def read():
            async with Fetcher(tmp_path / 'actual-fetcher', offline=True, respect_robots=False) as f:
                candidate = Candidate(name='Public University', country='Synthetic', city='Synthetic',
                                      domain='public.invalid', costs_url=poisoned)
                _, result = await WebCostAdapter(f, '2027/28').fetch(candidate)
                return result, dict(f.stats)

        result, stats = asyncio.run(read())
        with factory() as session:
            run = session.get(ResearchRun, run_id)
            runner = ResearchRunner(session, run, p, settings(tmp_path), worker_id='synthetic-peer')
            runner._record_diagnostics(result.errors)
            runner._record_page_outcomes(result.page_outcomes)
            run.pages_checked, run.pages_failed = result.pages_checked, result.pages_failed
            run.retry_urls = result.retry_urls
            # An explicit fixture audit uses actual native _audit and SQL commit.
            # It is not a claim that the product automatically emits this event.
            runner._audit('synthetic_adapter_diagnostic', 'run', run_id,
                          errors=result.errors, page_outcomes=[asdict(v) for v in result.page_outcomes])
            runner._save()
        with factory() as fresh:
            row = fresh.get(ResearchRun, run_id)
            audit = fresh.scalar(select(AuditEvent).where(AuditEvent.entity_id == run_id))
            persisted = {'errors': row.errors, 'unknowns': row.unknowns, 'retry_urls': row.retry_urls,
                         'audit_detail': audit.detail, 'stage': row.stage,
                         'pages_checked': row.pages_checked, 'pages_failed': row.pages_failed}
            assert fresh.scalar(select(ClaimRow.id).limit(1)) is None
        payload = api_read(factory, org_id, run_id)
        record('p4-real-sql-api', {'persisted': persisted, 'API': payload, 'fetch_stats': stats,
                                 'API_auth': 'native tenant guard with explicit synthetic Principal dependency; no session login proof'})
        assert persisted['pages_checked'] == persisted['pages_failed'] == 1
        assert persisted['unknowns'] == ['prior unresolved source'] and payload['claims_recorded'] == 0
        assert 'refused_privacy' in ' '.join(payload['errors'])
        assert 'no requirements' not in ' '.join(payload['unknowns'])
        assert stats['refused_privacy'] == 1
        assert_absent(marker, {'persisted': persisted, 'API': payload})
    finally:
        engine.dispose()


def test_p5_real_enqueue_claim_Worker_dispatch_SQL_API_error(tmp_path, monkeypatch, caplog):
    marker = 'A_SQL_WORKER_EMAIL@example.invalid'
    engine, factory, _, (org_id, _, run_id) = fixture_db(tmp_path)
    worker_id = 'actual-synthetic-worker'

    @contextmanager
    def owned_scope():
        with factory() as session:
            try:
                yield session
                session.commit()
            except BaseException:
                session.rollback()
                raise

    monkeypatch.setattr('app.jobs.worker.session_scope', owned_scope)

    async def validation_fixture(self):
        return None

    async def native_privacy_escape_fixture(self, fetcher):
        # Only the stage's input is synthetic/injected; execute/_dispatch/
        # run_to_decision/_save/_audit/JobStore.fail and SQL remain unmocked.
        try:
            raise ValueError(marker)
        except ValueError:
            DiscoveryIntent(institution='Public University', domain='public.invalid',
                            degree=DegreeLevel.BACHELOR, field='Mathematics ' + marker)

    monkeypatch.setattr(ResearchRunner, '_stage_validate', validation_fixture)
    monkeypatch.setattr(ResearchRunner, '_stage_discover', native_privacy_escape_fixture)
    caplog.set_level(logging.INFO)
    try:
        with factory() as session:
            store = JobStore(session, worker_id=worker_id)
            job_id = store.enqueue('research', run_id=run_id, max_attempts=3).job_id
            session.commit()
            job = store.claim_next(worker_id=worker_id)
            assert job.id == job_id and job.attempts == 1
            session.commit()
        worker = Worker(settings(tmp_path), worker_id=worker_id)

        async def execute():
            await worker.execute(job_id)
            assert not [t for t in asyncio.all_tasks() if t is not asyncio.current_task() and not t.done()]

        asyncio.run(execute())
        with factory() as fresh:
            run = fresh.get(ResearchRun, run_id)
            job = fresh.get(Job, job_id)
            events = fresh.scalars(select(AuditEvent).where(AuditEvent.entity_id == run_id)).all()
            persisted = {'run_stage': run.stage, 'run_errors': run.errors, 'run_unknowns': run.unknowns,
                         'job_status': job.status, 'job_attempts': job.attempts,
                         'job_last_error': job.last_error, 'job_available_at': job.available_at,
                         'audit': [{'action': v.action, 'detail': v.detail} for v in events]}
            assert fresh.scalar(select(ClaimRow.id).limit(1)) is None
        payload = api_read(factory, org_id, run_id)
        records = [{'message': r.getMessage(), 'exc_info': r.exc_info is not None,
                    'context': repr(r.args)} for r in caplog.records]
        record('p5-real-sql-api', {'persisted': persisted, 'API': payload, 'logs': records,
                                 'Worker_dispatch': 'native unmocked', 'synthetic_boundary': 'injected stage exception only',
                                 'API_job_selection': 'future-backoff job may be filtered by native _view; durable Job.last_error checked separately'})
        assert persisted['run_stage'] == 'failed' and persisted['job_status'] == 'queued'
        assert persisted['job_attempts'] == 1 and worker.jobs_failed == 1 and worker.jobs_done == 0
        assert persisted['run_unknowns'] == ['prior unresolved source']
        assert any(v['action'] == 'run_failed' for v in persisted['audit'])
        assert 'QueryPrivacyError' in persisted['job_last_error']
        assert payload['stage'] == 'failed' and payload['claims_recorded'] == 0
        assert_absent(marker, {'persisted': persisted, 'API': payload, 'logs': records})
        assert all(not v['exc_info'] for v in records if 'failed' in v['message'])
    finally:
        engine.dispose()


@pytest.mark.parametrize('prior_failed_target', [False, True])
def test_p6_successful_offsite_guard_keeps_current_target(prior_failed_target, monkeypatch):
    # Fetcher normally blocks cross-site redirects/cache. This is the existing
    # defensive adapter contract, not a claim that that fetcher's guard failed.
    monkeypatch.setattr('app.adapters.requirements.web_requirements.TOPIC_SEARCH', False)
    first = 'https://public.invalid/first'
    second = 'https://public.invalid/second'
    final = 'https://other.invalid/elsewhere'
    requested = second if prior_failed_target else first
    results = []
    if prior_failed_target:
        results.append(FetchResult(url=first, outcome=FetchOutcome.HTTP_ERROR, status_code=404, error='HTTP 404'))
    results.append(FetchResult(url=requested, outcome=FetchOutcome.FETCHED, status_code=200,
                               content=b'<h1>Remote page</h1>', final_url=final))
    getter = AsyncMock(side_effect=results)
    candidate = Candidate(name='Public University', country='Synthetic', city='Synthetic',
                          domain='public.invalid', admissions_url=second if prior_failed_target else None)
    program = CandidateProgram(name='BSc Mathematics', degree=DegreeLevel.BACHELOR,
                               field='Mathematics', url=first)
    try:
        result = asyncio.run(WebRequirementsAdapter(SimpleNamespace(get=getter), '2027/28').verify(
            candidate, program, 'fall 2027'))
    except Exception as exc:
        record('p6-offsite-' + str(prior_failed_target), {'exception': repr(exc), 'native_get_boundary_calls': getter.await_count})
        raise
    record('p6-offsite-' + str(prior_failed_target), {'result': asdict(result), 'native_get_boundary_calls': getter.await_count,
                                                  'qualification': 'synthetic typed successful-result adapter boundary, no real Fetcher egress claim'})
    assert result.pages_checked == result.pages_failed == (2 if prior_failed_target else 1)
    assert not result.claims
    assert result.page_outcomes[-1].url == requested, 'current offsite outcome reused previous failed target URL'
    assert result.page_outcomes[-1].detail == 'redirected off the source site'
