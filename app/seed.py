from datetime import date

from app.auth import hash_password
from app.config import get_settings
from app.db import SessionLocal, engine
from app.models import AdminUser, Base, Credential, Education, Experience, Profile, Project, Skill, SkillCategory, Status


def seed() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.query(Profile).first():
            return
        profile = Profile(full_name="Ada Analyst", headline="Data and analytics engineer",
                          summary="I build reliable data products that turn complex questions into measurable outcomes.",
                          location="Remote", email="hello@example.com", status=Status.PUBLISHED)
        db.add(profile)
        db.flush()
        experience = Experience(profile_id=profile.id, company_name="Example Labs", title="Analytics Engineer",
                                start_date=date(2023, 1, 1), is_current=True, summary="Built trusted reporting foundations.",
                                status=Status.PUBLISHED, sort_order=1)
        project = Project(profile_id=profile.id, title="Customer Health Signals",
                          short_description="A practical ML system for prioritizing customer outreach.",
                          status=Status.PUBLISHED, sort_order=1)
        category = SkillCategory(profile_id=profile.id, name="Data & Engineering", status=Status.PUBLISHED, sort_order=1)
        db.add_all([experience, project, category])
        db.flush()
        db.add(Skill(profile_id=profile.id, category_id=category.id, name="Python", proficiency_level="Advanced", status=Status.PUBLISHED))
        db.add(Education(profile_id=profile.id, institution_name="University", degree_name="B.S. Data Science", status=Status.PUBLISHED))
        db.add(Credential(profile_id=profile.id, title="Data Analytics Certificate", issuer="Example Institute", status=Status.PUBLISHED))
        db.commit()
        if not db.query(AdminUser).filter_by(username=get_settings().admin_username).first():
            db.add(AdminUser(username=get_settings().admin_username, password_hash=hash_password(get_settings().admin_password)))
            db.commit()


if __name__ == "__main__":
    seed()
