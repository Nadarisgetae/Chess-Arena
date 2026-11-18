import re
from pathlib import Path

root = Path(__file__).parent.parent
js_content = (root / "frontend" / "app.js").read_text(encoding="utf-8")
html_content = (root / "frontend" / "index.html").read_text(encoding="utf-8")

ids_in_js = set(re.findall(r"(?:\$|getElementById)\(\s*['\"]([^'\"]+)['\"]\s*\)", js_content))
ids_in_html = set(re.findall(r"id=['\"]([^'\"]+)['\"]", html_content))

missing_ids = ids_in_js - ids_in_html
print(f"Total IDs referenced in JS: {len(ids_in_js)}")
print(f"Total IDs in HTML: {len(ids_in_html)}")
print(f"Missing IDs in HTML: {missing_ids}")
