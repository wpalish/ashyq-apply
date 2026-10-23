"""Own semantic expectations for the pinned external Round6 candidate."""
from dataclasses import asdict
import socket

import pytest

from replay_independent_scope_negatives import CASES, legacy, page, proposal


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setattr(proposal,'PROGRAMME_IDENTITY_BEFORE_FUNDING',False)
    def denied(*args,**kwargs):
        raise AssertionError('No network permitted')
    monkeypatch.setattr(socket,'getaddrinfo',denied)
    monkeypatch.setattr(socket,'create_connection',denied)
    monkeypatch.setattr(socket.socket,'connect',denied)


@pytest.mark.parametrize('name,body,expected',CASES,ids=[x[0] for x in CASES])
def test_off_retains_exact_original_classification(name,body,expected):
    html=page(body);url='https://example.edu/support/computer-science'
    assert asdict(proposal.classify_page(url=url,html=html)) == asdict(legacy.classify_page(url=url,html=html))


@pytest.mark.parametrize('name,body,expected',CASES,ids=[x[0] for x in CASES])
def test_enabled_matches_independent_page_purpose(name,body,expected,monkeypatch):
    monkeypatch.setattr(proposal,'PROGRAMME_IDENTITY_BEFORE_FUNDING',True)
    actual=proposal.classify_page(url='https://example.edu/support/computer-science',html=page(body))
    assert actual.page_type.value==expected
    assert actual.accepts('program_exists') is (expected=='program_detail')
