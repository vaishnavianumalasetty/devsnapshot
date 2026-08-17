from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates"))

CATEGORY_ORDER = [
    "Python Projects",
    "SQL Projects",
    "Web / App Development",
    "Machine Learning",
    "Data Analytics & BI",
    "Other Projects",
]


def categorize_repo(repo: dict) -> str:
    lang = (repo.get("language") or "").lower()
    desc = (repo.get("description") or "").lower()
    name = (repo.get("name") or "").lower()
    text = f"{desc} {name}"

    if "power bi" in text or "dax" in text or "dashboard" in text:
        return "Data Analytics & BI"
    if lang == "jupyter notebook" or "ml" in text or "prediction" in text or "forecasting" in text:
        return "Machine Learning"
    if "sql" in text and lang != "python":
        return "SQL Projects"
    if lang in ("python",):
        return "Python Projects"
    if lang in ("java", "html", "javascript", "typescript"):
        return "Web / App Development"
    return "Other Projects"


def categorize_repos(repos: list) -> dict:
    categorized = {}
    for repo in repos:
        category = categorize_repo(repo)
        categorized.setdefault(category, []).append(repo)

    # Reorder according to CATEGORY_ORDER, skipping empty categories
    ordered = {
        category: categorized[category]
        for category in CATEGORY_ORDER
        if category in categorized
    }
    return ordered


def generate_readme(username: str, repos: list) -> str:
    template = env.get_template("readme_template.md")
    categorized = categorize_repos(repos)
    return template.render(username=username, categorized_repos=categorized)
