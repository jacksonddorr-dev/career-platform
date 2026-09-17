from datetime import date

from app.content import build_public_profile
from app.models import Achievement, Experience, Profile, Project, Skill, SkillCategory, Status


def test_public_content_excludes_drafts_and_archived_records(db_session):
    profile = Profile(full_name="Ada Analyst", headline="Data scientist", summary="Builds useful models.", status=Status.PUBLISHED)
    db_session.add(profile)
    db_session.flush()
    published_experience = Experience(profile_id=profile.id, company_name="Published Co", title="Analyst", start_date=date(2024, 1, 1), status=Status.PUBLISHED, sort_order=1)
    draft_experience = Experience(profile_id=profile.id, company_name="Draft Co", title="Hidden", status=Status.DRAFT, sort_order=0)
    archived_project = Project(profile_id=profile.id, title="Archived", short_description="Not public", status=Status.ARCHIVED)
    category = SkillCategory(profile_id=profile.id, name="Tools", status=Status.PUBLISHED)
    db_session.add_all([published_experience, draft_experience, archived_project, category])
    db_session.flush()
    db_session.add(Skill(profile_id=profile.id, category_id=category.id, name="Python", proficiency_level="Advanced", status=Status.PUBLISHED))
    db_session.add(Achievement(experience_id=published_experience.id, text="Improved reporting", status=Status.PUBLISHED))
    db_session.commit()

    content = build_public_profile(db_session)

    assert content.profile.full_name == "Ada Analyst"
    assert [item.company_name for item in content.experience] == ["Published Co"]
    assert content.projects == []
    assert content.skill_categories[0].skills[0].name == "Python"
    assert content.experience[0].achievements[0].text == "Improved reporting"


def test_public_content_requires_a_published_profile(db_session):
    db_session.add(Profile(full_name="Draft Person", headline="Draft", status=Status.DRAFT))
    db_session.commit()

    content = build_public_profile(db_session)

    assert content is None
