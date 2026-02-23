import re
from collections import Counter

def count_chapters(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    chapters = re.split(r'^## ', content, flags=re.MULTILINE)
    results = []
    for ch in chapters:
        if not ch.strip():
            continue
        lines = ch.strip().split('\n')
        heading = lines[0].strip()
        if re.match(r'^[IVXLCDM]+', heading):
            text = '\n'.join(lines[1:])
            word_count = len(text.split())
            results.append((heading, word_count))
    return results

print('=== ORIGINAL (English) ===')
basedir = '/home/jo/biblioteca-universal-arion/obres/narrativa/txekhov/sala-numero-6/'
orig = count_chapters(basedir + 'original.md')
for heading, wc in orig:
    print('  ## %s: ~%d words' % (heading, wc))
print('  TOTAL chapters: %d' % len(orig))
print('  TOTAL words: ~%d' % sum(wc for _, wc in orig))

print()
print('=== TRANSLATION (Catalan) ===')
trad = count_chapters(basedir + 'traduccio.md')
for heading, wc in trad:
    print('  ## %s: ~%d words' % (heading, wc))
print('  TOTAL chapters: %d' % len(trad))
print('  TOTAL words: ~%d' % sum(wc for _, wc in trad))

print()
print('=== COMPARISON ===')
orig_headings = [h for h, _ in orig]
trad_headings = [h for h, _ in trad]
orig_set = set(orig_headings)
trad_set = set(trad_headings)

missing_in_trad = orig_set - trad_set
if missing_in_trad:
    print('  Missing in translation: %s' % missing_in_trad)
else:
    print('  No chapters missing from translation.')

orig_counts = Counter(orig_headings)
trad_counts = Counter(trad_headings)
orig_dupes = {k: v for k, v in orig_counts.items() if v > 1}
trad_dupes = {k: v for k, v in trad_counts.items() if v > 1}

if orig_dupes:
    print('  Duplicate chapters in original: %s' % orig_dupes)
else:
    print('  No duplicate chapters in original.')
if trad_dupes:
    print('  Duplicate chapters in translation: %s' % trad_dupes)
else:
    print('  No duplicate chapters in translation.')

print()
print('=== WORD COUNT RATIO PER CHAPTER (Translation/Original) ===')
for i in range(min(len(orig), len(trad))):
    oh, ow = orig[i]
    th, tw = trad[i]
    ratio = tw / ow if ow > 0 else 0
    print('  %s: %d orig -> %d trad (ratio: %.2f)' % (oh, ow, tw, ratio))
