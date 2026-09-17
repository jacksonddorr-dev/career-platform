from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Status(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160))
    headline: Mapped[str] = mapped_column(String(240))
    summary: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(160), default="")
    email: Mapped[str] = mapped_column(String(320), default="")
    website_url: Mapped[str] = mapped_column(String(500), default="")
    linkedin_url: Mapped[str] = mapped_column(String(500), default="")
    github_url: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.DRAFT, index=True)
    experiences: Mapped[list["Experience"]] = relationship(cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(cascade="all, delete-orphan")
    skill_categories: Mapped[list["SkillCategory"]] = relationship(cascade="all, delete-orphan")
    education: Mapped[list["Education"]] = relationship(cascade="all, delete-orphan")
    credentials: Mapped[list["Credential"]] = relationship(cascade="all, delete-orphan")


class Experience(TimestampMixin, Base):
    __tablename__ = "experiences"
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"))
    company_name: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(160), default="")
    employment_type: Mapped[str] = mapped_column(String(80), default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.DRAFT, index=True)
    achievements: Mapped[list["Achievement"]] = relationship(cascade="all, delete-orphan")


class Achievement(TimestampMixin, Base):
    __tablename__ = "achievements"
    id: Mapped[int] = mapped_column(primary_key=True)
    experience_id: Mapped[int] = mapped_column(ForeignKey("experiences.id"))
    text: Mapped[str] = mapped_column(Text)
    metric_value: Mapped[str] = mapped_column(String(100), default="")
    metric_label: Mapped[str] = mapped_column(String(160), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.DRAFT, index=True)


class Project(TimestampMixin, Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"))
    title: Mapped[str] = mapped_column(String(200))
    short_description: Mapped[str] = mapped_column(Text, default="")
    long_description: Mapped[str] = mapped_column(Text, default="")
    project_url: Mapped[str] = mapped_column(String(500), default="")
    repo_url: Mapped[str] = mapped_column(String(500), default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.DRAFT, index=True)
    highlights: Mapped[list["ProjectHighlight"]] = relationship(cascade="all, delete-orphan")


class ProjectHighlight(TimestampMixin, Base):
    __tablename__ = "project_highlights"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    text: Mapped[str] = mapped_column(Text)
    metric_value: Mapped[str] = mapped_column(String(100), default="")
    metric_label: Mapped[str] = mapped_column(String(160), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.DRAFT, index=True)


class SkillCategory(TimestampMixin, Base):
    __tablename__ = "skill_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"))
    name: Mapped[str] = mapped_column(String(160))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.DRAFT, index=True)
    skills: Mapped[list["Skill"]] = relationship(cascade="all, delete-orphan")


class Skill(TimestampMixin, Base):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("skill_categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(160))
    proficiency_level: Mapped[str] = mapped_column(String(80), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.DRAFT, index=True)


class Education(TimestampMixin, Base):
    __tablename__ = "education"
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"))
    institution_name: Mapped[str] = mapped_column(String(240))
    degree_name: Mapped[str] = mapped_column(String(200), default="")
    field_of_study: Mapped[str] = mapped_column(String(200), default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    honors: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.DRAFT, index=True)


class Credential(TimestampMixin, Base):
    __tablename__ = "credentials"
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"))
    title: Mapped[str] = mapped_column(String(240))
    issuer: Mapped[str] = mapped_column(String(200), default="")
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    credential_url: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.DRAFT, index=True)


class AdminUser(TimestampMixin, Base):
    __tablename__ = "admin_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
