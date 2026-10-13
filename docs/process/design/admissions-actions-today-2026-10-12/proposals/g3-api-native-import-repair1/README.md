# G3 native import repair1

Only the newly added API test import is corrected to existing app.config.get_settings. The first focused runner did not execute tests: the wrong module caused two collection errors. Native settings/config/tests remain unchanged. Root reviewed complete two import hunks below; installed Ruff applies import sorting only. NOT_APPLIED / NOT_RUN.

--- a/backend/tests/test_admissions_actions_api.py
+++ b/backend/tests/test_admissions_actions_api.py
@@ -18,6 +18,7 @@
 import pytest
 from sqlalchemy import delete, event
 
+from app.config import get_settings
 from app.domain import admissions_actions as d
 from app.models import (
     AuthSession,
@@ -33,7 +34,6 @@
 from app.schemas import admissions_actions as s
 from app.schemas.result import DocumentChecklist, DocumentItem, Scholarship
 from app.security import DEV_ORGANIZATION_ID, DEV_USER_ID, token_hash
-from app.settings import get_settings
 from tests.test_admissions_actions_concurrency import (
     create_profile_only,
     current_values,
