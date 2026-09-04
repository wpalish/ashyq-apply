"""The social module's storage: profiles, posts, threads and what deleting means.

The social graph is deliberately *not* tenant-scoped — see the module docstring
of `app.models.social` — so these tests also pin down the boundary: a social row
carries no organization, and nothing here can reach an applicant case.
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.domain.enums import ApplicantStatus
from app.domain.social import (
    MAX_POST_TAGS,
    POST_MAX_CHARS,
    extract_tags,
    normalize_key,
)
from app.models import (
    Organization,
    OrganizationMembership,
    Post,
    PostReply,
    PostTag,
    SocialProfile,
    SocialProfileUniversity,
    User,
)


def make_user(session, suffix: str) -> User:
    """A registered account, exactly as `/api/auth/register` leaves one."""
    user = User(
        email=f"{suffix}@example.test",
        display_name=suffix.title(),
        password_hash="scrypt$16384$8$1$00$00",
    )
    org = Organization(name=f"{suffix.title()} Workspace", slug=f"{suffix}-workspace")
    session.add_all([user, org])
    session.flush()
    session.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role="owner"))
    return user


@pytest.fixture
def social_session(tmp_path):
    """A migrated SQLite database.

    Migrated rather than created with `create_all`, so the migration itself is
    under test on every run.
    """
    from app.db import migrate_to_head

    url = f"sqlite:///{tmp_path / 'social.db'}"
    migrate_to_head(url)
    engine = sa.create_engine(url)
    session = sessionmaker(bind=engine, future=True)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class TestNormalization:
    def test_one_university_written_three_ways_gives_one_key(self):
        assert normalize_key("KBTU") == normalize_key("kbtu") == normalize_key("K.B.T.U.")

    def test_spacing_and_punctuation_do_not_split_a_city(self):
        assert normalize_key("  Нур-Султан ") == normalize_key("нур султан")

    def test_a_value_with_no_letters_or_digits_normalizes_to_nothing(self):
        assert normalize_key("—  —") == ""

    def test_kazakh_letters_survive_normalization(self):
        """`а-я` does not contain ә, ғ, қ, ң, ө, ұ, ү or і. A narrower
        character class deletes half of a Kazakh university's name."""
        assert normalize_key("Әл-Фараби") == "әл-фараби"

    def test_tags_are_extracted_in_order_without_duplicates(self):
        assert extract_tags("Кто в #KBTU? Я тоже в #kbtu, еду в #Astana") == ["KBTU", "Astana"]

    def test_a_post_cannot_carry_unlimited_tags(self):
        body = " ".join(f"#tag{i}" for i in range(MAX_POST_TAGS + 5))
        assert len(extract_tags(body)) == MAX_POST_TAGS


class TestTheMigrationAndTheCodeAgree:
    """A migration must not import the application, so the limits are written
    down twice. This is what stops the two copies drifting apart."""

    def test_the_limits_in_the_migration_match_the_domain(self):
        import importlib

        migration = importlib.import_module("migrations.versions.e7c4a91b6f20_social_module")
        from app.domain import social

        assert migration.POST_MAX_CHARS == social.POST_MAX_CHARS
        assert migration.REPLY_MAX_CHARS == social.REPLY_MAX_CHARS
        assert migration.BIO_MAX_CHARS == social.BIO_MAX_CHARS


class TestSocialProfile:
    def test_a_new_profile_states_no_status_rather_than_guessing_one(self, social_session):
        user = make_user(social_session, "aigerim")
        social_session.add(SocialProfile(user_id=user.id))
        social_session.commit()

        profile = social_session.get(SocialProfile, user.id)
        assert profile.status is None
        assert profile.bio == ""

    def test_a_profile_keeps_what_was_typed_and_what_is_indexed(self, social_session):
        user = make_user(social_session, "dias")
        social_session.add(
            SocialProfile(
                user_id=user.id,
                status=ApplicantStatus.ACCEPTED,
                target_city="Astana",
                target_major="Computer Science",
                bio="Готовлюсь к SAT.",
            )
        )
        social_session.commit()

        profile = social_session.get(SocialProfile, user.id)
        assert profile.target_city == "Astana"
        assert profile.target_city_key == "astana"
        assert profile.target_major_key == "computer-science"
        assert profile.status == ApplicantStatus.ACCEPTED

    def test_target_universities_are_rows_so_the_filter_can_use_an_index(self, social_session):
        user = make_user(social_session, "madina")
        profile = SocialProfile(user_id=user.id)
        profile.universities = [
            SocialProfileUniversity(name="KBTU"),
            SocialProfileUniversity(name="Nazarbayev University"),
        ]
        social_session.add(profile)
        social_session.commit()

        keys = {row.name_key for row in social_session.get(SocialProfile, user.id).universities}
        assert keys == {"kbtu", "nazarbayev-university"}

    def test_the_same_university_cannot_be_listed_twice(self, social_session):
        user = make_user(social_session, "timur")
        profile = SocialProfile(user_id=user.id)
        profile.universities = [
            SocialProfileUniversity(name="KBTU"),
            SocialProfileUniversity(name="k.b.t.u."),
        ]
        social_session.add(profile)
        with pytest.raises(IntegrityError):
            social_session.commit()

    def test_a_profile_carries_no_organization(self):
        """Discover is global. If this column ever appears, the feature broke."""
        assert "organization_id" not in SocialProfile.__table__.columns


class TestPostsAndThreads:
    def test_a_post_belongs_to_its_author_and_carries_its_tags(self, social_session):
        user = make_user(social_session, "ayana")
        post = Post(author_id=user.id, body="Кто подаётся в #KBTU в этом году?")
        post.tags = [PostTag(label="KBTU")]
        social_session.add(post)
        social_session.commit()

        stored = social_session.query(Post).one()
        assert stored.author.display_name == "Ayana"
        assert [(tag.label, tag.key) for tag in stored.tags] == [("KBTU", "kbtu")]

    def test_a_reply_hangs_off_a_post_and_never_appears_in_the_feed(self, social_session):
        author = make_user(social_session, "arman")
        answerer = make_user(social_session, "zhanel")
        post = Post(author_id=author.id, body="Какой минимальный IELTS в KBTU?")
        social_session.add(post)
        social_session.flush()
        social_session.add(PostReply(post_id=post.id, author_id=answerer.id, body="6.0 overall."))
        social_session.commit()

        # The feed is `SELECT FROM posts`. Replies live in their own table, so
        # there is no filter to forget.
        assert social_session.query(Post).count() == 1
        assert social_session.query(PostReply).count() == 1
        assert social_session.query(Post).one().replies[0].body == "6.0 overall."

    def test_the_database_refuses_a_post_longer_than_the_limit(self, social_session):
        user = make_user(social_session, "nurlan")
        social_session.add(Post(author_id=user.id, body="x" * (POST_MAX_CHARS + 1)))
        with pytest.raises(IntegrityError):
            social_session.commit()

    def test_an_empty_post_is_refused(self, social_session):
        user = make_user(social_session, "saltanat")
        social_session.add(Post(author_id=user.id, body="   "))
        with pytest.raises(IntegrityError):
            social_session.commit()


class TestDeletion:
    def test_deleting_an_account_erases_its_social_footprint(self, social_session):
        user = make_user(social_session, "alua")
        other = make_user(social_session, "bekzat")
        profile = SocialProfile(user_id=user.id)
        profile.universities = [SocialProfileUniversity(name="KBTU")]
        post = Post(author_id=user.id, body="Всем привет #Astana")
        post.tags = [PostTag(label="Astana")]
        social_session.add_all([profile, post])
        social_session.flush()
        social_session.add(PostReply(post_id=post.id, author_id=other.id, body="Привет!"))
        social_session.commit()

        social_session.delete(social_session.get(User, user.id))
        social_session.commit()

        assert social_session.query(SocialProfile).count() == 0
        assert social_session.query(SocialProfileUniversity).count() == 0
        assert social_session.query(Post).count() == 0
        assert social_session.query(PostTag).count() == 0
        # Someone else's reply lived on that post; it goes with the post.
        assert social_session.query(PostReply).count() == 0
        # ...and the person who wrote it still has an account.
        assert social_session.get(User, other.id) is not None

    def test_deleting_a_post_takes_its_thread_with_it(self, social_session):
        user = make_user(social_session, "gulnara")
        post = Post(author_id=user.id, body="Вопрос про дедлайны")
        social_session.add(post)
        social_session.flush()
        social_session.add(PostReply(post_id=post.id, author_id=user.id, body="Апаю"))
        social_session.commit()

        social_session.delete(social_session.query(Post).one())
        social_session.commit()
        assert social_session.query(PostReply).count() == 0


class TestPostgresEnforcesItToo:
    """The ORM issues the cascades; PostgreSQL is what actually holds the line."""

    def test_the_foreign_keys_cascade_in_the_real_database(self, pg_engine):
        factory = sessionmaker(bind=pg_engine, future=True)
        session = factory()
        try:
            user = make_user(session, "postgres-user")
            post = Post(author_id=user.id, body="Пост в постгресе")
            session.add_all([SocialProfile(user_id=user.id), post])
            session.flush()
            session.add(PostReply(post_id=post.id, author_id=user.id, body="Ответ"))
            session.commit()

            # Delete by statement, so the ORM's own cascade cannot be what passes.
            session.execute(sa.text("DELETE FROM users WHERE id = :id"), {"id": user.id})
            session.commit()

            assert session.query(SocialProfile).count() == 0
            assert session.query(Post).count() == 0
            assert session.query(PostReply).count() == 0
        finally:
            session.close()
