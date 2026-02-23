import re

path = "/home/jo/biblioteca-universal-arion/obres/filosofia/marc-aureli/meditacions/traduccio.md"
with open(path, "r") as f:
    content = f.read()

print("=== Header check ===")
print("Starts with '# Meditacions':", content.startswith("# Meditacions"))

print("\n=== Footer check ===")
last_100 = content[-100:]
print("Last 100 chars:", repr(last_100))

print("\n=== Book headers ===")
book_headers = re.findall(r"^## Llibre .+$", content, re.MULTILINE)
print("Book headers found:", len(book_headers))
for h in book_headers:
    print("  ", h)

print("\n=== Section counts per book ===")
books = re.split(r"^## Llibre ", content, flags=re.MULTILINE)
for b in books[1:]:
    book_name = b.split("\n")[0].strip()
    sections = re.findall(r"^### \d+\.\d+", b, re.MULTILINE)
    print("  Llibre {}: {} sections".format(book_name, len(sections)))

total_sections = len(re.findall(r"^### \d+\.\d+", content, re.MULTILINE))
print("\nTotal section headers:", total_sections)
