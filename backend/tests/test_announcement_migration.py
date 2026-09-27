"""Test legacy announcement target enum migration."""

from app.database import SessionLocal, engine, Base
from app.models.comms import Announcement, AnnouncementTarget


def test_legacy_section_announcement_migrated():
    """Verify legacy SECTION announcements can be loaded after migration."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        # Insert a legacy SECTION announcement (before migration)
        from sqlalchemy import text
        session.execute(text("DELETE FROM announcements"))
        session.execute(text(
            "INSERT INTO announcements (title, content, target_type, published_by, published_at, priority, is_pinned) "
            "VALUES ('Legacy SECTION Announcement', 'Test', 'SECTION', 1, CURRENT_TIMESTAMP, 'NORMAL', FALSE)"
        ))
        session.commit()

        # After migration, SECTION should be EVERYONE and loadable
        session.rollback()
        session.execute(text(
            "UPDATE announcements SET target_type = 'EVERYONE' WHERE target_type = 'SECTION'"
        ))
        session.commit()

        # Should now load without LookupError
        ann = session.query(Announcement).filter(Announcement.title == "Legacy SECTION Announcement").first()
        assert ann is not None
        assert ann.target_type == AnnouncementTarget.EVERYONE
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
