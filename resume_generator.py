import os
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from utils.readme_generator import categorize_repos

env = Environment(loader=FileSystemLoader("templates"))


def render_resume_html(username: str, repos: list, max_total: int = 8) -> str:
    template = env.get_template("resume_template.html")
    categorized = categorize_repos(repos)

    # Flatten in category order, then cap the total
    limited = {}
    count = 0
    for category, repo_list in categorized.items():
        if count >= max_total:
            break
        remaining_slots = max_total - count
        selected = repo_list[:remaining_slots]
        if selected:
            limited[category] = selected
            count += len(selected)

    return template.render(username=username, categorized_repos=limited)


def generate_resume_pdf(username: str, repos: list, output_path: str = "resume_output.pdf") -> str:
    html_content = render_resume_html(username, repos)

    with open("temp_resume.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto("file://" + os.path.abspath("temp_resume.html"))
        page.pdf(path=output_path, print_background=True)
        browser.close()

    return output_path