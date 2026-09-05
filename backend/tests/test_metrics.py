"""What the process will admit about itself to a scraper.

An operator watching this service had the logs and nothing else: no way to see
that the queue was filling, that a stage was wedged, or that the limiter was
turning real users away. These are the numbers that answer those questions,
and the endpoint that carries them must never become a second way to read
applicant data.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app import metrics


@pytest.fixture(autouse=True)
def _empty_registry():
    """Counters are process-global; a test must not read another's numbers."""
    metrics.reset()
    yield
    metrics.reset()


@pytest.fixture
def client(tmp_path, monkeypatch, corpus_dir):
    """A client backed by a throwaway database and the bundled corpus."""
    from app.config import Settings, get_settings

    settings = Settings(
        demo_mode=True,
        database_url=f"sqlite:///{tmp_path / 'metrics.db'}",
        cache_dir=tmp_path / "cache",
        export_dir=tmp_path / "exports",
        corpus_dir=corpus_dir,
        fetch_delay_seconds=0.0,
        enable_browser_tier=False,
    )
    settings.ensure_dirs()
    get_settings.cache_clear()
    monkeypatch.setattr("app.config.get_settings", lambda: settings)

    import app.db as db_module

    engine = db_module.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", db_module.sessionmaker(bind=engine, future=True))
    db_module.migrate_to_head(settings.database_url)

    import app.main as main_module

    # The middleware reads the settings captured at import. Point them at this
    # test's copy so the token and the enabled flag are the ones under test.
    monkeypatch.setattr(main_module, "settings", settings)

    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


@pytest.fixture
def configure(monkeypatch):
    """Set the endpoint's own settings the way a deployment does: through env.

    The route resolves `get_settings()` at call time, so this exercises the
    real path from environment to behaviour rather than reaching past it.
    """
    # Taken from the route module rather than from `app.config`: the client
    # fixture replaces the name in `app.config`, while the route still calls the
    # cached original it imported. That original is the one to clear.
    from app.api.routes_metrics import get_settings

    def apply(**env: str):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()

    yield apply
    get_settings.cache_clear()


def samples(body: str, name: str) -> dict[str, float]:
    """Every sample of one metric, keyed on its label set as written."""
    found = {}
    for line in body.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        match = re.match(rf"^{re.escape(name)}(\{{.*?\}})? (\S+)$", line)
        if match:
            found[match.group(1) or ""] = float(match.group(2))
    return found


class TestTheFormat:
    def test_a_scraper_gets_prometheus_text_not_json(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert "version=0.0.4" in response.headers["content-type"]

    def test_every_metric_declares_its_help_and_type(self, client):
        body = client.get("/metrics").text
        named = {line.split()[2] for line in body.splitlines() if line.startswith("# TYPE")}
        assert named, "no metric declared a type"
        for name in named:
            assert f"# HELP {name} " in body, f"{name} is typed but never explained"

    def test_the_histogram_buckets_are_cumulative_and_end_in_infinity(self, client):
        client.get("/api/health")
        body = client.get("/metrics").text

        buckets = samples(body, "ashyq_http_request_duration_seconds_bucket")
        assert buckets, "no latency buckets were rendered"
        values = [v for _, v in sorted(buckets.items(), key=lambda kv: _bucket_bound(kv[0]))]
        assert values == sorted(values), "buckets must not decrease"

        total = samples(body, "ashyq_http_request_duration_seconds_count")[""]
        assert values[-1] == total, "the +Inf bucket must hold every observation"
        assert '{le="+Inf"}' in buckets


def _bucket_bound(label: str) -> float:
    bound = re.search(r'le="([^"]+)"', label)
    assert bound
    return float("inf") if bound.group(1) == "+Inf" else float(bound.group(1))


class TestWhatIsCounted:
    def test_a_request_is_counted_under_its_route_not_its_url(self, client):
        """A run id in a metric label is an unbounded set of time series.

        Prometheus keeps one series per distinct label set, so counting raw
        paths turns a week of normal use into a memory leak in the scraper.
        """
        started = client.post("/api/profiles", json=_demo_profile())
        assert started.status_code in (200, 201)

        body = client.get("/metrics").text
        labels = " ".join(samples(body, "ashyq_http_requests_total"))
        assert 'route="/api/profiles"' in labels
        assert "/api/runs/" not in labels

    def test_the_scrape_itself_is_not_counted(self, client):
        """Otherwise the busiest endpoint in every deployment is the scraper."""
        client.get("/metrics")
        body = client.get("/metrics").text
        assert 'route="/metrics"' not in " ".join(samples(body, "ashyq_http_requests_total"))

    def test_a_refused_request_is_counted_with_the_status_it_was_refused_with(self, client):
        for _ in range(3):
            client.get("/api/runs/does-not-exist")
        body = client.get("/metrics").text
        counted = {
            k: v for k, v in samples(body, "ashyq_http_requests_total").items() if "404" in k
        }
        assert sum(counted.values()) == 3

    def test_turning_a_user_away_is_visible(self, client):
        """The limiter used to refuse silently: no log line, no number, no alert."""
        limit = 10  # auth_rate_limit_per_minute
        for _ in range(limit + 2):
            client.post("/api/auth/login", json={"email": "a@example.com", "password": "x" * 12})

        body = client.get("/metrics").text
        refusals = samples(body, "ashyq_rate_limited_total")
        assert refusals, "a 429 left no trace in the metrics"
        assert sum(refusals.values()) == 2
        assert 'group="auth"' in " ".join(refusals)


class TestWhatTheDatabaseContributes:
    def test_jobs_and_runs_are_reported_by_state(self, client):
        client.post("/api/profiles", json=_demo_profile())
        body = client.get("/metrics").text

        assert "ashyq_jobs" in body
        assert "ashyq_runs" in body

    def test_an_unreachable_database_does_not_take_the_endpoint_down(self, client, monkeypatch):
        """A metrics endpoint that fails with the database is blind exactly when
        an operator needs it most: the process counters still answer."""
        import app.db as db_module

        def refuse(*_args, **_kwargs):
            raise RuntimeError("database is gone")

        monkeypatch.setattr(db_module, "SessionLocal", refuse)

        response = client.get("/metrics")
        assert response.status_code == 200
        assert "ashyq_http_requests_total" in response.text
        assert "ashyq_metrics_database_errors_total 1" in response.text


class TestWhoMayRead:
    def test_no_applicant_data_reaches_the_scraper(self, client):
        """Everything here is an aggregate. The name is the test's canary."""
        profile = _demo_profile()
        profile["display_name"] = "Aigerim Nurlanovna (canary)"
        client.post("/api/profiles", json=profile)

        body = client.get("/metrics").text
        assert "Aigerim" not in body
        assert "canary" not in body

    def test_a_configured_token_is_required(self, client, configure):
        configure(UNIMATCH_METRICS_TOKEN="s3cret-token")

        assert client.get("/metrics").status_code == 401
        assert client.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert client.get("/metrics", headers={"Authorization": "s3cret-token"}).status_code == 401
        allowed = client.get("/metrics", headers={"Authorization": "Bearer s3cret-token"})
        assert allowed.status_code == 200

    def test_the_endpoint_can_be_switched_off_entirely(self, client, configure):
        configure(UNIMATCH_METRICS_ENABLED="false")
        # 404, not 403: a disabled endpoint should not advertise that it exists.
        assert client.get("/metrics").status_code == 404


class TestTheProductionGuard:
    def test_production_refuses_to_serve_metrics_without_a_token(self):
        from app.config import Settings

        settings = Settings(
            environment="production",
            auth_enabled=True,
            cookie_secure=True,
            database_url="postgresql+psycopg://u:p@db/unimatch",
            cors_origins="https://apply.example.com",
            email_sender="smtp",
            smtp_host="smtp.example.com",
            public_base_url="https://apply.example.com",
            metrics_enabled=True,
            metrics_token="",
        )
        with pytest.raises(RuntimeError, match="UNIMATCH_METRICS_TOKEN"):
            settings.validate_runtime()

    def test_a_token_or_a_closed_endpoint_both_satisfy_it(self):
        from app.config import Settings

        base = {
            "environment": "production",
            "auth_enabled": True,
            "cookie_secure": True,
            "database_url": "postgresql+psycopg://u:p@db/unimatch",
            "cors_origins": "https://apply.example.com",
            "email_sender": "smtp",
            "smtp_host": "smtp.example.com",
            "public_base_url": "https://apply.example.com",
        }
        Settings(
            **base, metrics_enabled=True, metrics_token="a-long-enough-token"
        ).validate_runtime()
        Settings(**base, metrics_enabled=False, metrics_token="").validate_runtime()


def _demo_profile() -> dict:
    from app.corpus.demo_profile import DEMO_PROFILE

    return DEMO_PROFILE.model_dump(mode="json")
