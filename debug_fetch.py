import urllib.request, urllib.parse, re

url = 'https://hu.wikisource.org/wiki/Nemzeti_dal'
parsed = urllib.parse.urlsplit(url)
encoded_path = urllib.parse.quote(parsed.path, safe='/:@')
url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, encoded_path, parsed.query, parsed.fragment))
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req)
text = resp.read().decode('utf-8')

idx = text.find('mw-parser-output')
if idx > 0:
    print(text[idx:idx+5000])
