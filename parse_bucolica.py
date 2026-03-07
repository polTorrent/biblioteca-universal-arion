import re
import html

with open("bucolica_wiki.html") as f:
    content = f.read()

start = content.find('<div class="mw-parser-output">')
if start == -1:
    print("NOT FOUND")
    exit(1)

end = content.find("<!-- \nNewPP", start)
if end == -1:
    end = len(content)

body = content[start:end]
body = re.sub(r"<br\s*/?>", "\n", body)
body = re.sub(r"</p>", "\n\n", body)
body = re.sub(r"<[^>]+>", "", body)
body = html.unescape(body)

lines = [l.rstrip() for l in body.split("\n")]
for l in lines[:80]:
    print(l)
print("...[TRUNCATED]...")
