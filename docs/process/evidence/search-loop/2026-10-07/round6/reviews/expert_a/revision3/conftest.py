"""Opt-in external source loader; default run remains the repository control."""
import importlib
import importlib.util
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
if os.environ.get('EXPERT_A_ROUND6_REVISION3') == '1':
    for name,filename in (
        ('app.adapters.page_classifier','proposed_page_classifier.py'),
        ('app.adapters.scholarship.web_scholarships','proposed_web_scholarships.py'),
    ):
        package=importlib.import_module(name.rsplit('.',1)[0])
        spec=importlib.util.spec_from_file_location(name,ROOT/filename)
        module=importlib.util.module_from_spec(spec)
        sys.modules[name]=module
        spec.loader.exec_module(module)
        setattr(package,name.rsplit('.',1)[1],module)
