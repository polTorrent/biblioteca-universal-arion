import re

with open("/home/jo/biblioteca-universal-arion/obres/filosofia/nietzsche/aurora/_buch1_aph1.html") as f:
    content = f.read()

# Find sidebar/navigation links to other aphorisms in Erstes Buch
links = re.findall(r'href="(/nietzsche/schriften/morgenroete/[^"]+)"[^>]*>([^<]+)', content)
for href, text in links:
    if href != "/nietzsche/schriften/morgenroete/vorrede" and href != "/nietzsche/schriften/morgenroete/titel":
        print(f"{text.strip()} -> {href}")
