import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import make_session, require_admin, verify_password
from app.config import get_settings
from app.content import PublicProfile, build_public_profile
from app.db import get_db
from app.models import (Achievement, AdminUser, Credential, Education, Experience, Profile, Project,
                        ProjectHighlight, Skill, SkillCategory, Status)
from app.media import validate_media_reference
from app.resume import resume_response
from app.snapshot import SnapshotStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("career_platform")
settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.state.snapshot_store = SnapshotStore()


def current_content(db: Session) -> tuple[PublicProfile, bool]:
    try:
        content = build_public_profile(db)
        if content:
            app.state.snapshot_store.save(content)
            return content, False
    except Exception as exc:
        logger.warning("public database render failed; using fallback: %s", exc)
    cached = app.state.snapshot_store.load()
    if cached:
        logger.info("public profile served from snapshot fallback")
        return cached, True
    raise HTTPException(status_code=503, detail="Public profile is not available")


def render(request: Request, db: Session, section: str, title: str, intro: str = ""):
    content, fallback = current_content(db)
    template = "home.html" if section == "home" else "section.html"
    return templates.TemplateResponse(request=request, name=template, context={"content": content, "settings": settings,
                                                                                "section": section, "title": title,
                                                                                "intro": intro, "fallback": fallback})


@app.get("/", response_class=HTMLResponse)
def root(request: Request, db: Session = Depends(get_db)):
    return render(request, db, "home", "Home")


@app.get("/about", response_class=HTMLResponse)
def about(request: Request, db: Session = Depends(get_db)):
    return render(request, db, "about", "About")


@app.get("/experience", response_class=HTMLResponse)
def experience(request: Request, db: Session = Depends(get_db)):
    return render(request, db, "experience", "Experience")


@app.get("/projects", response_class=HTMLResponse)
def projects(request: Request, db: Session = Depends(get_db)):
    return render(request, db, "projects", "Projects")


@app.get("/skills", response_class=HTMLResponse)
def skills(request: Request, db: Session = Depends(get_db)):
    return render(request, db, "skills", "Skills")


@app.get("/education", response_class=HTMLResponse)
def education(request: Request, db: Session = Depends(get_db)):
    return render(request, db, "education", "Education & Credentials")


@app.get("/contact", response_class=HTMLResponse)
def contact(request: Request, db: Session = Depends(get_db)):
    return render(request, db, "contact", "Contact")


@app.get("/resume.pdf")
def resume(db: Session = Depends(get_db)):
    content, _ = current_content(db)
    return resume_response(content)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "career-platform"}


@app.post("/api/v1/auth/login")
def login(username: str = Form(...), password: str = Form(...),
          db: Session = Depends(get_db)):
    try:
        user = db.query(AdminUser).filter_by(username=username).first()
    except Exception:
        user = next((item for item in db.identity_map.values()
                     if isinstance(item, AdminUser) and item.username == username), None)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    result = JSONResponse({"authenticated": True, "username": username})
    result.set_cookie("session", make_session(username), httponly=True, secure=False, samesite="lax")
    return result


@app.post("/api/v1/auth/logout")
def logout():
    result = JSONResponse({"authenticated": False})
    result.delete_cookie("session")
    return result


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, user: AdminUser = Depends(require_admin)):
    return HTMLResponse(f"<html><body><h1>Admin</h1><p>Signed in as {user.username}</p></body></html>")


@app.get("/api/v1/admin/profile")
def admin_profile(user: AdminUser = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        profile = db.query(Profile).order_by(Profile.id).first()
    except Exception:
        profile = None
    if not profile:
        return {"profile": None}
    return {"profile": {key: value.value if isinstance(value, Status) else value
                        for key, value in profile.__dict__.items() if not key.startswith("_")}}


@app.put("/api/v1/admin/profile")
def update_profile(payload: dict, user: AdminUser = Depends(require_admin), db: Session = Depends(get_db)):
    profile = db.query(Profile).order_by(Profile.id).first()
    if not profile:
        profile = Profile(full_name=payload.get("full_name", ""), headline=payload.get("headline", ""))
        db.add(profile)
    for key in ("full_name", "headline", "summary", "location", "email", "website_url", "linkedin_url", "github_url"):
        if key in payload:
            setattr(profile, key, payload[key])
    if payload.get("status") in {status.value for status in Status}:
        profile.status = Status(payload["status"])
    db.commit()
    return {"ok": True, "id": profile.id}


@app.post("/api/v1/admin/profile/{action}")
def profile_action(action: str, user: AdminUser = Depends(require_admin), db: Session = Depends(get_db)):
    profile = db.query(Profile).order_by(Profile.id).first()
    if not profile or action not in {"publish", "archive", "draft"}:
        raise HTTPException(status_code=400, detail="Invalid profile action")
    profile.status = {"publish": Status.PUBLISHED, "archive": Status.ARCHIVED, "draft": Status.DRAFT}[action]
    db.commit()
    return {"ok": True, "status": profile.status.value}


@app.post("/api/v1/admin/media/validate")
def validate_media(payload: dict, user: AdminUser = Depends(require_admin)):
    try:
        return {"valid": True, "url": validate_media_reference(payload.get("url", ""), payload.get("content_type"))}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


CONTENT_MODELS = {
    "experience": Experience, "achievements": Achievement, "projects": Project,
    "highlights": ProjectHighlight, "skill-categories": SkillCategory, "skills": Skill,
    "education": Education, "credentials": Credential,
}


@app.post("/api/v1/admin/{kind}")
def create_content(kind: str, payload: dict, user: AdminUser = Depends(require_admin),
                   db: Session = Depends(get_db)):
    model = CONTENT_MODELS.get(kind)
    if model is None:
        raise HTTPException(status_code=404, detail="Unknown content type")
    allowed = {column.name for column in model.__table__.columns if column.name not in {"id", "created_at", "updated_at"}}
    item = model(**{key: value for key, value in payload.items() if key in allowed})
    db.add(item)
    db.commit()
    return {"id": item.id, "status": item.status.value if isinstance(item.status, Status) else item.status}


@app.put("/api/v1/admin/{kind}/{item_id}")
def update_content(kind: str, item_id: int, payload: dict, user: AdminUser = Depends(require_admin),
                   db: Session = Depends(get_db)):
    model = CONTENT_MODELS.get(kind)
    item = db.get(model, item_id) if model else None
    if item is None:
        raise HTTPException(status_code=404, detail="Content not found")
    allowed = {column.name for column in model.__table__.columns if column.name not in {"id", "created_at", "updated_at"}}
    for key, value in payload.items():
        if key in allowed:
            setattr(item, key, value)
    db.commit()
    return {"ok": True, "id": item.id}


@app.post("/api/v1/admin/{kind}/{item_id}/{action}")
def content_action(kind: str, item_id: int, action: str, user: AdminUser = Depends(require_admin),
                   db: Session = Depends(get_db)):
    model = CONTENT_MODELS.get(kind)
    item = db.get(model, item_id) if model else None
    if item is None or action not in {"publish", "archive", "draft"}:
        raise HTTPException(status_code=400, detail="Invalid content action")
    item.status = {"publish": Status.PUBLISHED, "archive": Status.ARCHIVED, "draft": Status.DRAFT}[action]
    db.commit()
    return {"ok": True, "status": item.status.value}
