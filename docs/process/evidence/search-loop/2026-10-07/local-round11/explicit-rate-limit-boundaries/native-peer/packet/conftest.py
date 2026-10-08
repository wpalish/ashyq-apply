"""Isolated test replay loader; never installed or imported by repository tests."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
import socket
import sys
from pathlib import Path

import pytest

B=Path(__file__).resolve().parent
REPO=B.parents[1]/'ashyq-apply/backend'
PLAN=json.loads((B/'PLAN.json').read_text())
sys.path.insert(0,str(REPO))

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pins():return {r:sha(REPO/r) for r in PLAN['app_original_sha256']}
def proposals():return {r:sha(B/'replay-source'/r) for r in PLAN['source_proposal_sha256']}
def test_pins():return {r:sha(B/'proposed'/r) for r in PLAN['ownership']}
BEFORE=pins();PROPOSAL_BEFORE=proposals();TEST_BEFORE=test_pins()
assert BEFORE==PLAN['app_original_sha256']
assert PROPOSAL_BEFORE==PLAN['source_proposal_sha256']

def deny(*args,**kwargs):raise AssertionError('Real DNS/socket/network forbidden in native test replay')
socket.socket.connect=deny
socket.socket.connect_ex=deny
socket.create_connection=deny
socket.getaddrinfo=deny

from app.adapters import search as frozen_search
from app.adapters.discovery import live_discovery as frozen_live
from app.adapters.search import exa_mcp as mcp
from app.adapters.search import retrieval as frozen_retrieval

METHODS={key:getattr(mcp.ExaMcpSearchProvider,key) for key in ['search','_search_once','_post','_initialize']}
LANE=os.environ['A_NATIVE_LANE']
assert LANE in {'off','on'}
assert frozen_search._THROTTLED_UNTIL=={}


def load(rel,name,package=False):
 options={'submodule_search_locations':[str(REPO/'app/adapters/search')]} if package else {}
 spec=importlib.util.spec_from_file_location(name,B/'replay-source'/rel,**options)
 obj=importlib.util.module_from_spec(spec);sys.modules[name]=obj;spec.loader.exec_module(obj)
 return obj

if LANE=='on':
 import app.adapters
 import app.adapters.discovery
 search=load('app/adapters/search/__init__.py','_native_proposed_search',True)
 for name,obj in list(sys.modules.items()):
  if name.startswith('app.adapters.search.') and '.' not in name[len('app.adapters.search.'):]:setattr(search,name.rsplit('.',1)[1],obj)
 sys.modules['app.adapters.search']=search;app.adapters.search=search
 retrieval=load('app/adapters/search/retrieval.py','_native_proposed_retrieval')
 sys.modules['app.adapters.search.retrieval']=retrieval;search.retrieval=retrieval
 live=load('app/adapters/discovery/live_discovery.py','_native_proposed_live')
 sys.modules['app.adapters.discovery.live_discovery']=live;app.adapters.discovery.live_discovery=live
else:
 search,retrieval,live=frozen_search,frozen_retrieval,frozen_live

@pytest.fixture(autouse=True)
def fresh_child_throttle():
 # Same ordinary repository isolation contract, in this fresh child only.
 search.reset_search_throttle()
 yield
 search.reset_search_throttle()


def pytest_sessionfinish(session,exitstatus):
 after=pins();prop_after=proposals();tests_after=test_pins()
 assert BEFORE==after
 assert PROPOSAL_BEFORE==prop_after
 assert TEST_BEFORE==tests_after
 assert all(getattr(mcp.ExaMcpSearchProvider,key) is value for key,value in METHODS.items())
 reporter=session.config.pluginmanager.get_plugin('terminalreporter')
 results={key:len(reporter.stats.get(key,[])) for key in ['passed','failed','skipped','error']}
 dest=B/os.environ['A_NATIVE_OUTPUT'];assert not dest.exists()
 dest.write_text(json.dumps({'lane':LANE,'exit':int(exitstatus),'pytest':results,'collected':session.testscollected,'original_app_before':BEFORE,'original_app_after':after,'proposal_app_before':PROPOSAL_BEFORE,'proposal_app_after':prop_after,'test_before':TEST_BEFORE,'test_after':tests_after,'native_method_identity_unchanged':True,'target_files':{'search':search.__file__,'retrieval':retrieval.__file__,'live':live.__file__},'socket_DNS_realtransport_denied':True,'app_repo_primarySTOP_or_throttle_reset':False},indent=2)+'\n')
