from jinja2 import Environment, FileSystemLoader
from utils.readme_generator import categorize_repos

env = Environment(loader=FileSystemLoader("templates"))

THEME_TEMPLATES = {
    "minimal": "portfolio_template.html",
    "bold": "portfolio_template_bold.html",
}


def generate_portfolio(username: str, repos: list, theme: str = "minimal") -> str:
    template_name = THEME_TEMPLATES.get(theme, "portfolio_template.html")
    template = env.get_template(template_name)
    categorized = categorize_repos(repos)
    return template.render(username=username, categorized_repos=categorized)
