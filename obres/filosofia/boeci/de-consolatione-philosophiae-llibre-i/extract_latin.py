import re, html

with open('/home/jo/biblioteca-universal-arion/obres/filosofia/boeci/de-consolatione-philosophiae-llibre-i/perseus.html', 'r') as f:
    text = f.read()

# Extract the text container
match = re.search(r'<div class="text_container la"[^>]*>(.*?)</div>\s*</div>\s*</div>', text, re.DOTALL)
if not match:
    match = re.search(r'<div class="text_container la"[^>]*>(.*)', text, re.DOTALL)

if not match:
    print('NO MATCH FOUND')
    exit(1)

content = match.group(1)

# Remove line numbers
content = re.sub(r'<span[^>]*class="linenumber"[^>]*>.*?</span>', '', content, flags=re.DOTALL)

# Remove footnote divs
content = re.sub(r'<div class="footnotes[^"]*"[^>]*>.*?</div>', '', content, flags=re.DOTALL)

# Replace <br /> with newline
content = re.sub(r'<br\s*/?>', '\n', content)

# Replace <hr /> with section separator
content = re.sub(r'<hr\s*/?>', '\n---\n', content)

# Replace </blockquote> and <blockquote> with markers
content = re.sub(r'</blockquote>\s*<blockquote>', '\n\n', content)
content = re.sub(r'</?blockquote>', '\n', content)

# Remove page references [p. 130]
content = re.sub(r'\[p\.\s*\d+\]', '', content)

# Remove all remaining HTML tags
content = re.sub(r'<[^>]+>', '', content)

# Unescape HTML entities
content = html.unescape(content)

# Clean up whitespace
lines = content.strip().split('\n')
cleaned = [line.strip() for line in lines]
result = '\n'.join(cleaned)
result = re.sub(r'\n{3,}', '\n\n', result)

# Add section headers based on content structure
# The Perseus text alternates M (metrum) and P (prosa) sections

print(result[:5000])
print('\n...\n')
print(result[-1000:])
print('\nTOTAL LENGTH:', len(result))

with open('/home/jo/biblioteca-universal-arion/obres/filosofia/boeci/de-consolatione-philosophiae-llibre-i/latin_text.md', 'w') as f:
    f.write(result)
print('Written to latin_text.md')
