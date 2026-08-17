from fastapi import APIRouter, Request
from authlib.integrations.starlette_client import OAuth
from github import Github
from dotenv import load_dotenv
from datetime import datetime, timedelta
from models.database import SessionLocal, User, Repo
from utils.readme_generator import generate_readme
from utils.portfolio_generator import generate_portfolio
from utils.resume_generator import generate_resume_pdf
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os
import asyncio

load_dotenv()

router = APIRouter()
templates_engine = Jinja2Templates(directory="templates")

oauth = OAuth()
oauth.register(
    name="github",
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    access_token_url="https://github.com/login/oauth/access_token",
    authorize_url="https://github.com/login/oauth/authorize",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "read:user repo"},
)


def sync_if_stale(username: str, force: bool = False):
    db = SessionLocal()
    user = db.query(User).filter(User.github_username == username).first()

    if not user:
        db.close()
        return

    now = datetime.utcnow()
    stale_after = timedelta(hours=1)

    if not force and user.last_synced and (now - user.last_synced) < stale_after:
        db.close()
        return

    g = Github(user.access_token)
    gh_user = g.get_user()

    existing_repos = {r.name: r.included for r in db.query(Repo).filter(Repo.owner_username == username).all()}
    db.query(Repo).filter(Repo.owner_username == username).delete()

    for repo in gh_user.get_repos():
        db.add(Repo(
            owner_username=username,
            name=repo.name,
            description=repo.description,
            language=repo.language,
            stars=repo.stargazers_count,
            included=existing_repos.get(repo.name, True),
        ))

    user.last_synced = now
    db.commit()
    db.close()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    username = request.session.get("username")

    if not username:
        return templates_engine.TemplateResponse(request, "dashboard.html", {"logged_in": False})

    db = SessionLocal()
    user = db.query(User).filter(User.github_username == username).first()
    repo_count = db.query(Repo).filter(
        Repo.owner_username == username,
        Repo.name != username
    ).count()
    db.close()

    last_synced_str = "Never"
    if user and user.last_synced:
        delta = datetime.utcnow() - user.last_synced
        minutes = int(delta.total_seconds() // 60)
        if minutes < 1:
            last_synced_str = "Just now"
        elif minutes < 60:
            last_synced_str = f"{minutes} min ago"
        else:
            last_synced_str = f"{minutes // 60} hr ago"

    return templates_engine.TemplateResponse(request, "dashboard.html", {
        "logged_in": True,
        "username": username,
        "repo_count": repo_count,
        "last_synced_str": last_synced_str,
        "current_theme": user.theme if user else "minimal",
    })


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@router.get("/login")
async def login(request: Request):
    redirect_uri = "http://localhost:8000/auth/callback"
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.github.authorize_access_token(request)
    access_token = token["access_token"]

    g = Github(access_token)
    gh_user = g.get_user()
    username = gh_user.login

    db = SessionLocal()

    user = db.query(User).filter(User.github_username == username).first()
    if not user:
        user = User(github_username=username, access_token=access_token, last_synced=datetime.utcnow())
        db.add(user)
    else:
        user.access_token = access_token
        user.last_synced = datetime.utcnow()
    db.commit()

    existing_repos = {r.name: r.included for r in db.query(Repo).filter(Repo.owner_username == username).all()}
    db.query(Repo).filter(Repo.owner_username == username).delete()

    for repo in gh_user.get_repos():
        db.add(Repo(
            owner_username=username,
            name=repo.name,
            description=repo.description,
            language=repo.language,
            stars=repo.stargazers_count,
            included=existing_repos.get(repo.name, True),
        ))

    db.commit()
    db.close()

    request.session["username"] = username
    return RedirectResponse(url="/")


@router.get("/repos")
async def get_saved_repos(username: str):
    db = SessionLocal()
    repos = db.query(Repo).filter(
        Repo.owner_username == username,
        Repo.name != username
    ).all()
    db.close()

    return {
        "repo_count": len(repos),
        "repos": [
            {
                "name": r.name,
                "description": r.description,
                "language": r.language,
                "stars": r.stars,
            }
            for r in repos
        ],
    }


@router.get("/generate/readme", response_class=HTMLResponse)
async def generate_readme_endpoint(request: Request, username: str):
    await asyncio.to_thread(sync_if_stale, username)

    db = SessionLocal()
    repos = db.query(Repo).filter(
        Repo.owner_username == username,
        Repo.name != username,
        Repo.included == True
    ).all()
    db.close()

    repos_data = [
        {
            "name": r.name,
            "description": r.description,
            "language": r.language,
            "stars": r.stars,
        }
        for r in repos
    ]

    readme_content = generate_readme(username, repos_data)
    return templates_engine.TemplateResponse(request, "readme_viewer_template.html", {
        "username": username,
        "readme_content": readme_content,
    })


@router.get("/generate/portfolio", response_class=HTMLResponse)
async def generate_portfolio_endpoint(username: str):
    await asyncio.to_thread(sync_if_stale, username)

    db = SessionLocal()
    user = db.query(User).filter(User.github_username == username).first()
    theme = user.theme if user else "minimal"
    repos = db.query(Repo).filter(
        Repo.owner_username == username,
        Repo.name != username,
        Repo.included == True
    ).all()
    db.close()

    repos_data = [
        {
            "name": r.name,
            "description": r.description,
            "language": r.language,
            "stars": r.stars,
        }
        for r in repos
    ]

    return generate_portfolio(username, repos_data, theme=theme)


@router.get("/generate/resume-pdf")
async def generate_resume_pdf_endpoint(username: str):
    await asyncio.to_thread(sync_if_stale, username)

    db = SessionLocal()
    repos = db.query(Repo).filter(
        Repo.owner_username == username,
        Repo.name != username,
        Repo.included == True
    ).all()
    db.close()

    repos_data = [
        {
            "name": r.name,
            "description": r.description,
            "language": r.language,
            "stars": r.stars,
        }
        for r in repos
    ]

    output_path = await asyncio.to_thread(generate_resume_pdf, username, repos_data)
    return FileResponse(output_path, media_type="application/pdf", filename=f"{username}_resume.pdf")


@router.get("/sync")
async def sync_repos(username: str, force: bool = False):
    db = SessionLocal()
    user = db.query(User).filter(User.github_username == username).first()
    if not user:
        db.close()
        return {"error": "User not found. Please login first."}
    db.close()

    was_stale = force or not user.last_synced or (datetime.utcnow() - user.last_synced) >= timedelta(hours=1)
    await asyncio.to_thread(sync_if_stale, username, force)

    return {"synced": was_stale}


@router.get("/manage-repos", response_class=HTMLResponse)
async def manage_repos_page(request: Request, username: str):
    db = SessionLocal()
    repos = db.query(Repo).filter(
        Repo.owner_username == username,
        Repo.name != username
    ).all()
    db.close()

    return templates_engine.TemplateResponse(request, "manage_repos.html", {
        "username": username,
        "repos": repos,
    })


@router.post("/manage-repos/toggle")
async def toggle_repo_inclusion(request: Request):
    form = await request.form()
    username = form.get("username")
    repo_name = form.get("repo_name")

    db = SessionLocal()
    repo = db.query(Repo).filter(
        Repo.owner_username == username,
        Repo.name == repo_name
    ).first()
    if repo:
        repo.included = not repo.included
        db.commit()
    db.close()

    return RedirectResponse(url=f"/manage-repos?username={username}", status_code=303)


@router.post("/set-theme")
async def set_theme(request: Request):
    form = await request.form()
    username = form.get("username")
    theme = form.get("theme")

    db = SessionLocal()
    user = db.query(User).filter(User.github_username == username).first()
    if user and theme in ("minimal", "bold"):
        user.theme = theme
        db.commit()
    db.close()

    return RedirectResponse(url="/", status_code=303)
