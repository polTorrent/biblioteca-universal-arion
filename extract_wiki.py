import html, re

with open("bucolica_wiki.html") as f:
    content = f.read()

text = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
text = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL)
text = re.sub(r"<[^>]+>", "\n", text)
text = html.unescape(text)
lines = [l.strip() for l in text.split("\n") if l.strip()]
for l in lines:
    print(l)
