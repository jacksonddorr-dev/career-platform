from dataclasses import asdict, dataclass
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Credential, Education, Experience, Profile, Project, SkillCategory, Status


@dataclass
class PublicProfile:
    profile: Profile
    experience: list[Experience]
    projects: list[Project]
    skill_categories: list[SkillCategory]
    education: list[Education]
    credentials: list[Credential]

    def to_dict(self) -> dict:
        def scalar(obj):
            relationships = {"experiences", "projects", "skill_categories", "education", "credentials",
                             "achievements", "highlights", "skills"}
            return {k: (v.isoformat() if isinstance(v, date) else v.value if isinstance(v, Status) else v)
                    for k, v in obj.__dict__.items()
                    if not k.startswith("_") and k not in {"created_at", "updated_at"} and k not in relationships}
        return {
            "profile": scalar(self.profile),
            "experience": [{**scalar(item), "achievements": [scalar(a) for a in item.achievements if a.status == Status.PUBLISHED]} for item in self.experience],
            "projects": [{**scalar(item), "highlights": [scalar(h) for h in item.highlights if h.status == Status.PUBLISHED]} for item in self.projects],
            "skill_categories": [{**scalar(item), "skills": [scalar(s) for s in item.skills if s.status == Status.PUBLISHED]} for item in self.skill_categories],
            "education": [scalar(item) for item in self.education],
            "credentials": [scalar(item) for item in self.credentials],
        }


def build_public_profile(db: Session) -> PublicProfile | None:
    profile = db.scalar(select(Profile).where(Profile.status == Status.PUBLISHED).order_by(Profile.id))
    if profile is None:
        return None
    experience = list(db.scalars(select(Experience).options(selectinload(Experience.achievements)).where(
        Experience.profile_id == profile.id, Experience.status == Status.PUBLISHED).order_by(Experience.sort_order, Experience.id)))
    projects = list(db.scalars(select(Project).options(selectinload(Project.highlights)).where(
        Project.profile_id == profile.id, Project.status == Status.PUBLISHED).order_by(Project.sort_order, Project.id)))
    categories = list(db.scalars(select(SkillCategory).options(selectinload(SkillCategory.skills)).where(
        SkillCategory.profile_id == profile.id, SkillCategory.status == Status.PUBLISHED).order_by(SkillCategory.sort_order, SkillCategory.id)))
    education = list(db.scalars(select(Education).where(Education.profile_id == profile.id, Education.status == Status.PUBLISHED).order_by(Education.end_date.desc().nullslast(), Education.id)))
    credentials = list(db.scalars(select(Credential).where(Credential.profile_id == profile.id, Credential.status == Status.PUBLISHED).order_by(Credential.issue_date.desc().nullslast(), Credential.id)))
    return PublicProfile(profile, experience, projects, categories, education, credentials)


def dict_to_profile(data: dict) -> PublicProfile:
    """Convert a cached snapshot to the small object shape used by templates."""
    from types import SimpleNamespace
    def obj(value):
        if isinstance(value, dict):
            return SimpleNamespace(**{k: obj(v) for k, v in value.items()})
        if isinstance(value, list):
            return [obj(v) for v in value]
        return value
    return PublicProfile(obj(data["profile"]), obj(data.get("experience", [])), obj(data.get("projects", [])),
                         obj(data.get("skill_categories", [])), obj(data.get("education", [])), obj(data.get("credentials", [])))
