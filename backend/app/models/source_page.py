"""SourcePage: one mutable row per fetched page — the crawler's memory.

Metadata only, never bodies: the URL, the HTTP validators and content hash
needed to ask "has this page changed?" on the next visit instead of
re-downloading it, and the counters the claim system owns.

Retention policy: metadata-only rows (never bodies); purgeable when
active_claims=0 AND fetched_at < now()-RETENTION_DAYS, or fetched_at IS NULL
AND created_at < now()-RETENTION_DAYS; active_claims>0 never purged;
RETENTION_DAYS=180 (owner may override 90); purge execution is T32's job.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase, utcnow

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

#: Days a page's metadata is kept after its last fetch. Must stay equal to
#: SOURCE_PAGE_RETENTION_DAYS in the ``source_pages`` migration — a migration
#: must not import the application, so the policy is written down twice and
#: the tests pin the copies together.
RETENTION_DAYS = 180


class SourcePage(TimestampedBase):
    """One row per fetched page, updated in place on every re-fetch.

    The unique index on ``url`` alone (not per version) is deliberate: this is
    a page's current state, not its history — a one-row-per-page shape is what
    lets ``active_claims`` and the retention sweep stay simple.
    """

    __tablename__ = "source_pages"
    __table_args__ = (
        Index("uq_source_pages_url", "url", unique=True),
        Index("ix_source_pages_domain", "registrable_domain"),
        Index("ix_source_pages_institution", "institution_key"),
        Index("ix_source_pages_retention", "active_claims", "fetched_at"),
    )

    url: Mapped[str] = mapped_column(Text, nullable=False)
    #: Caller-derived registrable domain (live_discovery derives it; the model
    #: only stores it, so models never import adapters).
    registrable_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    #: Which institution this page belongs to, when mapped. Claim-system
    #: property: ``record`` coalesces it, never overwrites an existing value.
    institution_key: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # --- conditional-GET validators and change detection --------------------
    etag: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_modified_header: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: sha256 hex of the normalized extracted text — drift is detected by
    #: re-hashing, never by keeping the body.
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    #: When a Last-Modified header was last observed for this page.
    lastmod_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: When this row's fetch metadata was last refreshed.
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Plain string, not an enum column: the page classifier's vocabulary
    #: evolves without a migration.
    page_type: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")

    #: Live claims referencing this page. Owned by the claim system — fetches
    #: never touch it, and anything above zero blocks purging.
    active_claims: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    @classmethod
    def record(
        cls,
        session: Session,
        *,
        url: str,
        registrable_domain: str,
        etag: str | None = None,
        last_modified_header: str | None = None,
        content_hash: str | None = None,
        http_status: int | None = None,
        page_type: str = "unknown",
        institution_key: str | None = None,
        lastmod_seen: datetime | None = None,
        fetched_at: datetime | None = None,
    ) -> SourcePage:
        """Insert or refresh a page's fetch metadata, atomically.

        A single ``INSERT .. ON CONFLICT (url) DO UPDATE`` — never
        select-then-insert — so two concurrent writers converge on one row
        instead of racing two inserts. On conflict the fetch metadata takes
        the passed values (a None overwrites: this fetch genuinely saw no
        validator), the ownership columns coalesce (an existing
        institution_key / lastmod_seen wins over None), and ``active_claims``
        is never touched. Flushes, never commits: the caller owns the
        transaction. The returned instance is persistent in ``session``.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        bind = session.get_bind()
        dialect_insert = pg_insert if bind.dialect.name == "postgresql" else sqlite_insert

        table = cls.__table__
        stmt = (
            dialect_insert(cls)
            .values(
                url=url,
                registrable_domain=registrable_domain,
                etag=etag,
                last_modified_header=last_modified_header,
                content_hash=content_hash,
                http_status=http_status,
                page_type=page_type,
                institution_key=institution_key,
                lastmod_seen=lastmod_seen,
                fetched_at=fetched_at,
            )
            .on_conflict_do_update(
                index_elements=[table.c.url],
                set_={
                    "etag": etag,
                    "last_modified_header": last_modified_header,
                    "content_hash": content_hash,
                    "http_status": http_status,
                    "page_type": page_type,
                    "fetched_at": fetched_at,
                    "updated_at": utcnow(),
                    # Ownership coalesces: a fetch that brings no mapping of its
                    # own must not wipe the one already recorded.
                    "institution_key": func.coalesce(table.c.institution_key, institution_key),
                    "lastmod_seen": func.coalesce(table.c.lastmod_seen, lastmod_seen),
                },
            )
        )
        session.execute(stmt)
        session.flush()
        # Materialize the upserted row as a persistent instance, so the
        # caller's further edits (claim counters) land on the same row.
        return session.query(cls).filter(cls.url == url).one()


def is_purgeable(
    fetched_at: datetime | None,
    created_at: datetime,
    active_claims: int,
    now: datetime,
) -> bool:
    """Whether the retention policy allows this row to be purged. Pure.

    Retention policy: metadata-only rows (never bodies); purgeable when
    active_claims=0 AND fetched_at < now()-RETENTION_DAYS, or fetched_at IS
    NULL AND created_at < now()-RETENTION_DAYS; active_claims>0 never purged;
    RETENTION_DAYS=180 (owner may override 90); purge execution is T32's job.
    The boundary itself (exactly RETENTION_DAYS old) is not purgeable: a row
    must be strictly older than the window.
    """
    if active_claims > 0:
        return False
    reference = fetched_at if fetched_at is not None else created_at
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now - reference > timedelta(days=RETENTION_DAYS)
