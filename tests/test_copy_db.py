from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.copy_db import copy_database
from app.models import Base, Experience, Profile, Status


def make_source(path):
    url = f"sqlite:///{path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        profile = Profile(id=7, full_name="Jackson", headline="Analyst", status=Status.PUBLISHED)
        db.add(profile)
        db.flush()
        db.add(Experience(id=42, profile_id=7, company_name="Acme", title="Intern", is_current=True,
                          start_date=date(2025, 6, 1), status=Status.PUBLISHED))
        db.commit()
    engine.dispose()
    return url


def make_target(path):
    url = f"sqlite:///{path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return url


def test_copy_preserves_ids_enums_dates_and_booleans(tmp_path):
    source, target = make_source(tmp_path / "src.db"), make_target(tmp_path / "dst.db")

    counts = copy_database(source, target)

    assert counts["profiles"] == 1 and counts["experiences"] == 1 and counts["skills"] == 0
    with Session(create_engine(target)) as db:
        exp = db.scalars(select(Experience)).one()
        assert (exp.id, exp.profile_id, exp.is_current, exp.start_date, exp.status) == \
               (42, 7, True, date(2025, 6, 1), Status.PUBLISHED)


def test_copy_refuses_non_empty_target_and_writes_nothing(tmp_path):
    source, target = make_source(tmp_path / "src.db"), make_target(tmp_path / "dst.db")
    copy_database(source, target)

    with pytest.raises(ValueError, match="not empty"):
        copy_database(source, target)

    with Session(create_engine(target)) as db:
        assert len(db.scalars(select(Profile)).all()) == 1
