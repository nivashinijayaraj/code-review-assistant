import subprocess
import json


def run_pylint(filepath):
    result = subprocess.run(
        ["pylint", filepath, "--output-format=json", "--disable=C0114,C0115,C0116,C0304"],
        capture_output=True,
        text=True,
    )
    issues = json.loads(result.stdout)

    # pylint's "type" tells us the category
    category_map = {
        "error": "bug",
        "fatal": "bug",
        "warning": "bug",
        "convention": "style",
        "refactor": "optimization",
    }

    found = []
    for issue in issues:
        if issue["symbol"] in ["eval-used", "exec-used"]:
            category = "security"
        elif issue["symbol"] in ["unused-import", "unused-variable"]:
            category = "style"
        else:
            category = category_map.get(issue["type"], "style")

        found.append({
            "line": issue["line"],
            "category": category,
            "message": issue["message"],
            "tool": "pylint",
        })
    return found


def run_bandit(filepath):
    result = subprocess.run(["bandit", filepath, "-f", "json"], capture_output=True, text=True)
    data = json.loads(result.stdout)

    found = []
    for issue in data["results"]:
        found.append({
            "line": issue["line_number"],
            "category": "security",
            "message": issue["issue_text"],
            "tool": "bandit",
        })
    return found


# Test: this part runs only when you run "python analyzer.py" directly
if __name__ == "__main__":
    all_issues = run_pylint("test.py") + run_bandit("test.py")
    for issue in all_issues:
        print(issue["line"], issue["category"], issue["tool"], issue["message"])