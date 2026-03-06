import re, subprocess, sys

def fetch_raw(title):
    url = "https://no.wikisource.org/w/index.php?title=" + title + "&action=raw"
    r = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
    return r.stdout

def clean_wikitext(text):
    text = re.sub(r'\{\{topp[^}]*\}\}', '', text)
    text = re.sub(r'\{\{bunn[^}]*\}\}', '', text)
    text = re.sub(r'\{\{prosa\}\}', '', text)
    text = re.sub(r'\{\{/prosa\}\}', '', text)
    text = re.sub(r'<pages[^/]*/>', '', text)
    text = re.sub(r'\[\[[^\]]*\|([^\]]*)\]\]', r'\1', text)
    text = re.sub(r'\[\[([^\]]*)\]\]', r'\1', text)
    text = text.replace("'''", '**')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

parts = [
    ("Et_Dukkehjem/F%C3%B8rste_akt", "Eerste akt"),
    ("Et_Dukkehjem/Annen_akt", "Annen akt"),
    ("Et_Dukkehjem/Tredje_akt", "Tredje akt"),
]

output = "# Et dukkehjem\n\n## Henrik Ibsen (1879)\n\n---\n\n"
output += "## Personerne\n\n"
output += "- **Advokat Helmer**\n"
output += "- **Nora**, hans hustru\n"
output += "- **Doktor Rank**\n"
output += "- **Fru Linde**\n"
output += "- **Sagforer Krogstad**\n"
output += "- **Helmers tre sma born**\n"
output += "- **Anne-Marie**, barnepige hos Helmers\n"
output += "- **Helene**, stuepige hos Helmers\n"
output += "- **Et bybud**\n\n"
output += "Handlingen foregar i Helmers bolig.\n\n---\n\n"

for url_part, title in parts:
    raw = fetch_raw(url_part)
    cleaned = clean_wikitext(raw)
    output += "## " + title + "\n\n" + cleaned + "\n\n---\n\n"

outpath = sys.argv[1] if len(sys.argv) > 1 else "original.md"
with open(outpath, "w") as f:
    f.write(output)

print("Written " + str(len(output)) + " chars to " + outpath)
