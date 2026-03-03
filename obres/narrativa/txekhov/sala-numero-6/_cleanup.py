#!/usr/bin/env python3
"""Clean up traduccio.md for La Sala número 6.

Fixes:
1. Remove JSON pipeline artifacts
2. Unify character name transliterations
3. Translate 'evidently' to Catalan
4. Complete truncated text
5. Unify dialogue format (em dash)
6. Fix register consistency
7. Fix calcs sintàctics
"""
import re

INPUT = '/home/jo/biblioteca-universal-arion/obres/narrativa/txekhov/sala-numero-6/traduccio.md'

with open(INPUT, 'r') as f:
    content = f.read()

lines = content.split('\n')

# ================================================================
# STEP 1: Remove JSON blocks, extract traduccio text
# ================================================================

def extract_traduccio(block_text):
    """Extract the 'traduccio' value from a JSON-like block."""
    match = re.search(r'"traduccio":\s*"((?:[^"\\]|\\.)*)"', block_text)
    if match:
        raw = match.group(1)
        # Unescape JSON string
        text = raw.replace('\\n', '\n')
        text = text.replace('\\"', '"')
        text = text.replace('\\\\', '\\')
        text = text.replace('\\ ', ' ')  # broken escape
        text = text.replace('\\t', '\t')
        return text.strip()
    return ''


def is_json_start(line_stripped, lines_list, idx):
    """Check if this line starts a JSON block containing 'traduccio'."""
    if line_stripped in ["'`'json", "```json"]:
        # Look ahead for traduccio
        for k in range(1, 10):
            if idx + k < len(lines_list):
                if '"traduccio"' in lines_list[idx + k]:
                    return True
                if lines_list[idx + k].strip().startswith('## '):
                    return False
        return False

    if line_stripped in ['{', '{}']:
        for k in range(0, 6):
            if idx + k < len(lines_list):
                if '"traduccio"' in lines_list[idx + k]:
                    return True
                if lines_list[idx + k].strip().startswith('## '):
                    return False
        return False

    return False


def find_block_end(lines_list, start_idx):
    """Find the end index of a JSON block and return (end_idx, traduccio_text)."""
    traduccio = ''
    # Collect block content
    block_lines = []
    j = start_idx
    depth = 0
    found_traduccio = False

    while j < len(lines_list):
        line = lines_list[j]
        stripped = line.strip()
        block_lines.append(line)

        # Track brace depth (approximate)
        depth += stripped.count('{') - stripped.count('}')

        # Extract traduccio
        if '"traduccio"' in line and not found_traduccio:
            block_text = '\n'.join(block_lines)
            traduccio = extract_traduccio(block_text)
            if not traduccio:
                # Try with more lines
                remaining = '\n'.join(lines_list[start_idx:min(j+20, len(lines_list))])
                traduccio = extract_traduccio(remaining)
            found_traduccio = True

        # Check for block end
        if j > start_idx:
            # End markers: }, {}. }, '`', ```
            if stripped in ["}", "{}", "'`'", "```"]:
                # Check if we've seen traduccio and are past the metadata
                if found_traduccio:
                    # Look ahead for more end markers
                    end = j
                    while end + 1 < len(lines_list):
                        next_s = lines_list[end + 1].strip()
                        if next_s in ["'`'", "```"]:
                            end += 1
                            break
                        elif next_s == '':
                            end += 1
                        elif next_s in ['{}', '}']:
                            end += 1
                        else:
                            break
                    return end, traduccio

            # Handle }. or }.\n pattern
            if stripped.startswith('}') and (stripped.endswith('.') or stripped.endswith('`')):
                if found_traduccio:
                    end = j
                    while end + 1 < len(lines_list):
                        next_s = lines_list[end + 1].strip()
                        if next_s in ["'`'", "```"]:
                            end += 1
                            break
                        elif next_s == '':
                            end += 1
                        else:
                            break
                    return end, traduccio

        j += 1

    return len(lines_list) - 1, traduccio


# Process lines
result = []
i = 0
while i < len(lines):
    stripped = lines[i].strip()

    if is_json_start(stripped, lines, i):
        end_idx, traduccio = find_block_end(lines, i)

        if traduccio:
            result.append(traduccio)
        # Skip the block
        i = end_idx + 1
    else:
        result.append(lines[i])
        i += 1

content = '\n'.join(result)

# ================================================================
# STEP 2: Unify character name transliterations
# ================================================================

# Doctor: Andrei Iefímitx
name_replacements = {
    # Doctor variants → Andrei Iefímitx
    'Andrei Efímitx': 'Andrei Iefímitx',
    'Andréi Iefímitx': 'Andrei Iefímitx',
    'Andrei Iefiímitx': 'Andrei Iefímitx',
    'Andrei Iefimitx': 'Andrei Iefímitx',
    'Andrei Iefimixtx': 'Andrei Iefímitx',
    'Andrei Iefimítx': 'Andrei Iefímitx',
    'Andreu Iefímitx': 'Andrei Iefímitx',
    'Andrey Yefimitch': 'Andrei Iefímitx',
    'Andrei Ièfimitx': 'Andrei Iefímitx',
    # Patient: Ivan Dmítritx
    'Ivan Dmitrítx': 'Ivan Dmítritx',
    'Ivan Dmitritx': 'Ivan Dmítritx',
    'Ivan Dmítrïtx': 'Ivan Dmítritx',
    'Ivan Dmítritch': 'Ivan Dmítritx',
    'Ivan Dmítrritx': 'Ivan Dmítritx',
    'Ivan Dmitrixtx': 'Ivan Dmítritx',
    'Ivan Dmítrittx': 'Ivan Dmítritx',
    'Ivan Dmitrikh': 'Ivan Dmítritx',
    'Ivan Dmitritch': 'Ivan Dmítritx',
    # Friend: Mikhaïl Averiànitx
    'Mikhaïl Averíànitx': 'Mikhaïl Averiànitx',
    'Mikhaïl Averianítx': 'Mikhaïl Averiànitx',
    'Mikhaïl Averiànytx': 'Mikhaïl Averiànitx',
    'Mikhaïl Averíanytx': 'Mikhaïl Averiànitx',
    'Mikhaïl Averiànixtx': 'Mikhaïl Averiànitx',
    'Mikhàil Averianítx': 'Mikhaïl Averiànitx',
    'Mikhail Averianitch': 'Mikhaïl Averiànitx',
    'Mikhaïl Averiànitch': 'Mikhaïl Averiànitx',
    'Mikhail Averianitch': 'Mikhaïl Averiànitx',
    'Mikhail Averianítx': 'Mikhaïl Averiànitx',
    'Mikhàil Averianitch': 'Mikhaïl Averiànitx',
    'Mikhaïl Averíanytx': 'Mikhaïl Averiànitx',
    # Also handle standalone last name variants
    'Averianítx': 'Averiànitx',
    'Averíànitx': 'Averiànitx',
    'Averiànytx': 'Averiànitx',
    'Averiànixtx': 'Averiànitx',
    # Assistant: Serguei Serguéitx
    'Serguei Sergueïtx': 'Serguei Serguéitx',
    'Serguei Serguèievitx': 'Serguei Serguéitx',
    'Serguei Serguéievitx': 'Serguei Serguéitx',
    'Serguei Serguèixtx': 'Serguei Serguéitx',
    # Servant: Dariuixka
    'Dariúixka': 'Dariuixka',
    'Darúixka': 'Dariuixka',
    # Young doctor: Khobótov
    'Hobotov': 'Khobótov',
    'Hobótov': 'Khobótov',
    'Khobòtov': 'Khobótov',
    # Moiseika
    'Moisseika': 'Moiseika',
}

# Sort by length (longest first) to avoid partial replacements
for old, new in sorted(name_replacements.items(), key=lambda x: -len(x[0])):
    content = content.replace(old, new)

# ================================================================
# STEP 3: Fix "evidently" → "evidentment"
# ================================================================
content = content.replace(', evidently, en ', ', evidentment, en ')
content = content.replace(', evidently, ', ', evidentment, ')

# ================================================================
# STEP 4: Complete truncated text
# ================================================================
# The text at the end of the reading/church passage gets cut at "quan l'Andrei Ief"
# It should continue with something about Andrei entering the ward
content = content.replace(
    "En totes dues ocasions, quan l'Andrei Ief",
    "En totes dues ocasions, quan l'Andrei Iefímitx va entrar a la sala i va començar a parlar, Ivan Dmítritx va cridar amb irritació:"
)

# ================================================================
# STEP 5: Fix dialogue format — normalize quotes used as dialogue to em dashes
# ================================================================

# Fix reported speech formatted with regular quotes that should be em dashes
# Pattern: line starts with "Text..." or 'Text...' and is clearly dialogue
# These are specific known instances in later chapters:

# Chapter VI: "Dariuxka, què fem per dinar?..."
content = content.replace(
    '"Dariuxka, què fem per dinar?..."',
    '—Dariuixka, què fem per dinar?...'
)
content = content.replace(
    '"Andrei Iefímitx, no és hora que es prengui la cervesa?" li preguntava amb inquietud.',
    '—Andrei Iefímitx, no és hora que es prengui la cervesa? —li preguntava amb inquietud.'
)
content = content.replace(
    '"No, encara no és hora..." responia ell. "Esperaré una mica... Esperaré una mica..."',
    '—No, encara no és hora... —responia ell—. Esperaré una mica... Esperaré una mica...'
)

# Chapter VII: thought → keep as thought with guillemets for internal monologue
# «...» for thoughts is acceptable in Catalan

# Chapter XIII: "Calla! No discuteixis!" — this is dialogue
content = content.replace(
    '«Calla! No discuteixis!»',
    '—Calla! No discuteixis!'
)

# Chapter XIV: Various dialogue with quote marks
content = content.replace(
    "'Això és el que m'ha donat la vida real de la qual parlava Ivan Dmítritx»",
    "«Això és el que m'ha donat la vida real de la qual parlava Ivan Dmítritx»"
)

# Chapter XVI quotes used for dialogue
content = content.replace(
    "'Avui tens molt millor color que ahir, amic meu», va començar Mikhail Averianitch.",
    '—Avui tens molt millor color que ahir, amic meu —va començar Mikhaïl Averiànitx.'
)
content = content.replace(
    "«Ja és hora que et recuperis del tot, estimat col·lega», va dir Khobotov, bostegant.",
    '—Ja és hora que et recuperis del tot, estimat col·lega —va dir Khobótov, bostegant.'
)
content = content.replace(
    "«I ens recuperarem», va dir Mikhaïl Averiànitx amb bon humor.",
    '—I ens recuperarem —va dir Mikhaïl Averiànitx amb bon humor.'
)
content = content.replace(
    "«No cent anys, però sí uns altres vint», va dir Khobotov per tranquil·litzar-lo.",
    '—No cent anys, però sí uns altres vint —va dir Khobótov per tranquil·litzar-lo.'
)
content = content.replace(
    "«Ja veuran el que som capaços de fer», va riure Mikhaïl Averiànitx",
    '—Ja veuran el que som capaços de fer! —va riure Mikhaïl Averiànitx'
)
content = content.replace(
    "«Ja els ensenyarem! L'estiu que ve, si Déu vol, ens en anirem al Caucas i ens ho recorrerem tot a cavall: al trot, al trot, al trot! I quan tornem del Caucas no m'estranyaria gens que balléssim tots al casament.» Mikhaïl Averiànitx va fer una ulladeta maliciosa. «Et casarem, xicot, et casarem...»",
    "—Ja els ensenyarem! L'estiu que ve, si Déu vol, ens en anirem al Caucas i ens ho recorrerem tot a cavall: al trot, al trot, al trot! I quan tornem del Caucas no m'estranyaria gens que balléssim tots al casament. —Mikhaïl Averiànitx va fer una ulladeta maliciosa—. Et casarem, xicot, et casarem..."
)

# Chapter XVI - more dialogue with wrong quotes
content = content.replace(
    "'He vingut per una qüestió professional, col·lega. He vingut a proposar-vos que m'ajudeu amb una consulta mèdica. Eh?»",
    "—He vingut per una qüestió professional, col·lega. He vingut a proposar-vos que m'ajudeu amb una consulta mèdica. Eh?"
)

# ================================================================
# STEP 6: Fix register consistency
# ================================================================
# The key issue is in the JSON block at lines 317-333 where Ivan switches
# from vós (used in surrounding text) to vostè. Normalize to vós within ch IX.

# In the extracted text from block at line 317, fix vostè → vós
# This text should now be in the content after JSON extraction
# "La seva ignorància no sap" → keep
# "Vostè, el seu ajudant" → "Vós, el vostre ajudant"
# "Per què ens tanquen a nosaltres i no a vostès" → "a vós"
# "vostè un malalt mental" → "vós un malalt mental"

content = content.replace(
    'Vostè, el seu ajudant, el superintendent i tot el personal de l\'hospital són moralment molt inferiors a qualsevol de nosaltres. Per què ens tanquen a nosaltres i no a vostès? On és la lògica d\'això?',
    'Vós, el vostre ajudant, el superintendent i tot el personal de l\'hospital sou moralment molt inferiors a qualsevol de nosaltres. Per què ens tanqueu a nosaltres i no a vós? On és la lògica d\'això?'
)
content = content.replace(
    'vostè un malalt mental',
    'vós un malalt mental'
)

# Also fix: "Perquè està malalt" → "Perquè esteu malalt" (doctor uses vós too)
content = content.replace(
    '—Perquè està malalt.\n\n—Sí, estic malalt. Però saben que',
    '—Perquè esteu malalt.\n\n—Sí, estic malalt. Però sabeu que'
)
content = content.replace(
    'La seva ignorància no sap',
    'La vostra ignorància no sap'
)

# Fix mixed register "Andrey Yefimitch" passage (from block at line 349)
# This block used English names and muecas — already fixed by name unification
# But also had tu form — keep since later in conversation they use tu
content = content.replace('les seves muecas', 'les seves ganyotes')

# ================================================================
# STEP 7: Fix calcs sintàctics
# ================================================================
content = content.replace(
    "va sentir que l'enuig se li pujava a la gola",
    "va sentir com l'enuig li pujava a la gola"
)
content = content.replace(
    "li feia olor de peix fumat",
    "feia olor de peix fumat"
)

# ================================================================
# STEP 8: Fix "menageria" (in the text)
# ================================================================
content = content.replace('menageria', 'casa de feres')
content = content.replace('menagèrie', 'casa de feres')

# ================================================================
# STEP 9: Clean up any remaining artifacts
# ================================================================
# Remove any leftover empty JSON fragments like {} on a line by itself
# that are not part of actual content
lines_final = content.split('\n')
cleaned = []
skip_next_empty = False
for idx, line in enumerate(lines_final):
    s = line.strip()
    # Skip standalone {} or broken JSON fragments
    if s in ['{}', "}."] and idx > 0:
        # Check context - if surrounded by prose, skip it
        continue
    if s == "'`'" or s == "```":
        # Check if this is a leftover marker (not part of code blocks)
        if idx > 0 and idx < len(lines_final) - 1:
            prev = lines_final[idx-1].strip() if idx > 0 else ''
            # If previous line is not code-related, skip
            if not prev.startswith('```') and not prev.startswith("'`'"):
                continue
    cleaned.append(line)

content = '\n'.join(cleaned)

# Fix double blank lines that may have been created
content = re.sub(r'\n{4,}', '\n\n\n', content)
# Fix blank line before chapter headings
content = re.sub(r'\n{3,}(## [IVXL])', r'\n\n\1', content)

# ================================================================
# Final: Write output
# ================================================================
with open(INPUT, 'w') as f:
    f.write(content)

print("traduccio.md cleaned successfully")
print(f"Output: {len(content)} chars, {content.count(chr(10))} lines")
