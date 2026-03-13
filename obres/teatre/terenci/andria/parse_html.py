import html, re

with open('obres/teatre/terenci/andria/tll.html', 'r') as f:
    text = f.read()

text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<br\s*/?>', '\n', text)
text = re.sub(r'</p>', '\n\n', text)
text = re.sub(r'<p[^>]*>', '', text)
text = re.sub(r'<[^>]+>', '', text)
text = html.unescape(text)

lines = text.split('\n')
cleaned = []
for line in lines:
    stripped = line.strip()
    if stripped:
        cleaned.append(stripped)
    elif cleaned and cleaned[-1] != '':
        cleaned.append('')

result = '\n'.join(cleaned)

start_idx = result.find('PROLOGVS')
if start_idx == -1:
    start_idx = result.upper().find('PROLOGUE')
if start_idx == -1:
    start_idx = 0

end_idx = result.find('The Latin Library')
if end_idx == -1:
    end_idx = len(result)

final = result[start_idx:end_idx].strip()

header = """# Andria — P. Terentius Afer (Terenci)

**Font**: [The Latin Library](https://www.thelatinlibrary.com/ter.andria.html)
**Llengua original**: llatí
**Data**: c. 166 aC

---

"""

with open('obres/teatre/terenci/andria/original.md', 'w') as f:
    f.write(header + final)

print(f"Saved {len(final)} chars to original.md")
print("First 300 chars:")
print(final[:300])
