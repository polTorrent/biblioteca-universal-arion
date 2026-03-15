#!/usr/bin/env python3
"""Fix all issues in Sala número 6 translation"""
import re

path = '/home/jo/biblioteca-universal-arion/obres/narrativa/txekhov/sala-numero-6/traduccio.md'

with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

original_len = len(text)

# ===== 1. FIX GRAMMAR =====
text = text.replace("Traduït del anglès", "Traduït de l'anglès")

# ===== 2. REMOVE DUPLICATE BLOCKS AND ARTIFACTS =====

# 2a. Remove duplicate justice paragraph (the one with "el sou" not "el seu sou")
dup_justice = (
    "\n\nNomés el temps dedicat a complir certes formalitats per les quals el jutge cobra el sou, "
    "i després... tot s'acaba. Aleshores pots cercar en va justícia i protecció en aquest poblet "
    "brut i miserable a cent cinquanta milles d'una estació de tren! I, de fet, no és absurd "
    "pensar tan sols en la justícia quan qualsevol tipus de violència és acceptada per la societat "
    "com una necessitat racional i coherent, i tot acte de misericòrdia —per exemple, un veredicte "
    "d'absolució— desperta una explosió de resentiment i esperit de venjança?"
)
if dup_justice in text:
    text = text.replace(dup_justice, "")
    print("✓ Removed duplicate justice paragraph")
else:
    print("✗ Could not find duplicate justice paragraph")

# 2b. Remove duplicate Chapter IV (second ## IV with "Ivan Dmitrikh")
dup_ch4 = (
    "\n## IV\n"
    "El veí d'Ivan Dmitrikh a l'esquerra és, com ja he dit, el jueu Moiseika; "
)
if dup_ch4 in text:
    # Find the full block to remove (ends before "—Felicita'm")
    start = text.find(dup_ch4)
    end_marker = "\n—Felicita'm"
    end = text.find(end_marker, start)
    if end != -1:
        text = text[:start] + "\n" + text[end:]
        print("✓ Removed duplicate Chapter IV")
else:
    print("✗ Could not find duplicate Chapter IV")

# 2c. Remove duplicate hospital description (with "Andrey Yefimitch va arribar a la ciutat per ocupar")
dup_hosp_start = "Quan Andrey Yefimitch va arribar a la ciutat per ocupar el seu càrrec"
if dup_hosp_start in text:
    start = text.find(dup_hosp_start)
    # Find end of this paragraph (double newline)
    end = text.find("\n\n", start)
    if end != -1:
        text = text[:start] + text[end + 2:]
        print("✓ Removed duplicate hospital description")
else:
    print("✗ Could not find duplicate hospital description")

# 2d. Remove first medicine/Pirogov duplicate (with "durant els últims vint-i-cinc anys")
dup_med_start = "D'altra banda, sabia perfectament que s'havia produït un canvi màgic en la medicina durant els últims vint-i-cinc anys."
if dup_med_start in text:
    start = text.find(dup_med_start)
    # This block spans until "una via d." truncated ending, then paragraph break
    end_marker = "una via d."
    truncated_end = text.find(end_marker, start)
    if truncated_end != -1:
        end = text.find("\n\n", truncated_end)
        if end != -1:
            text = text[:start] + text[end + 2:]
            print("✓ Removed duplicate medicine passage")
else:
    print("✗ Could not find duplicate medicine passage")

# 2e. Remove first Chapter VIII duplicate (with "[1]" footnote)
dup_viii_start = "## VIII\nDos anys abans, el Zemstvo, [1]"
if dup_viii_start in text:
    start = text.find(dup_viii_start)
    # Find end: after the footnote line
    footnote_text = "[1] Zemstvo:"
    fn_idx = text.find(footnote_text, start)
    if fn_idx != -1:
        end = text.find("\n\n", fn_idx)
        if end != -1:
            text = text[:start] + text[end + 2:]
            print("✓ Removed duplicate Chapter VIII")
else:
    print("✗ Could not find duplicate Chapter VIII")

# 2f. Remove misplaced town discussion in Chapter IX
# This block starts with "—Vols saber del poble o en general?" right after the angry encounter
# and goes through "Ivan Dmitritch escoltava amb atenció" + reaction
dup_town_start = "—Vols saber del poble o en general?\n—Bé, explica'm primer del poble"
if dup_town_start in text:
    start = text.find(dup_town_start)
    # Look backwards to include the blank line before
    if start > 0 and text[start-1] == '\n':
        start -= 1
    # Find the end: goes through news discussion until blank line before "Aquestes ximpleries"
    end_marker = "\n—Aquestes ximpleries"
    end = text.find(end_marker, start)
    if end != -1:
        text = text[:start] + text[end:]
        print("✓ Removed misplaced town discussion")
else:
    print("✗ Could not find misplaced town discussion")

# 2g. Remove duplicate Chapter X start (second "## X" header and content)
# The Chapter X that starts with "Ivan Dmítritx jeia en la mateixa posició"
# Keep the content from lines 179+ but add the intro from this duplicate
dup_x_header = "## X\nIvan Dm"
if dup_x_header in text:
    start = text.find(dup_x_header)
    # This duplicate goes until "Aviat es va saber per tot l'hospital"
    end_marker = "Aviat es va saber per tot l'hospital"
    end = text.find(end_marker, start)
    if end != -1:
        # Keep "Aviat es va saber..." and replace the ## X block
        text = text[:start] + text[end:]
        print("✓ Removed duplicate Chapter X start")
    else:
        print("✗ Could not find end of Chapter X duplicate")
else:
    print("✗ Could not find duplicate Chapter X header")

# 2h. Remove duplicate town hall scene (first version, with "Andrey Yefimitch/Yefimitch")
# This starts with "—Vaig tenir l'honor de proposar-vos fa deu anys —va prosseguir Andrey Yefimitch"
dup_townhall = "—Vaig tenir l'honor de proposar-vos fa deu anys —va prosseguir Andrey Yefimitch"
if dup_townhall in text:
    start = text.find(dup_townhall)
    # Look for start of paragraph (go back to newline)
    newline_before = text.rfind("\n", 0, start)
    if newline_before != -1:
        start = newline_before
    # This goes through to the JSON artifact "'`'"
    end_marker = "'`'\n"
    end = text.find(end_marker, start)
    if end != -1:
        end += len(end_marker)
        text = text[:start] + "\n" + text[end:]
        print("✓ Removed duplicate town hall scene + JSON artifact")
    else:
        print("✗ Could not find end of town hall duplicate")
else:
    print("✗ Could not find duplicate town hall scene")

# 2i. Remove duplicate mental exam response (first version, with "enrojar")
dup_exam = "En resposta a aquesta darrera pregunta, Andrei Iefímitx es va enrojar una mica"
if dup_exam in text:
    start = text.find(dup_exam)
    # Look for start (go to newline before)
    newline_before = text.rfind("\n", 0, start)
    if newline_before != -1:
        start = newline_before
    # Find end: through "es va sentir insultat i es va enfadar."
    end_marker = "es va sentir insultat i es va enfadar."
    end = text.find(end_marker, start)
    if end != -1:
        end += len(end_marker)
        # Also get the next line(s) about Mikhaïl visiting
        next_para = text.find("\n\n", end)
        # Check if next paragraph is about Mikhaïl visiting (duplicate of later content)
        if next_para != -1:
            next_content = text[next_para+2:next_para+50]
            if "Mikha" in next_content or "vespre del mateix dia" in next_content:
                end = text.find("\n\n", next_para + 2)
                if end != -1:
                    end += 2
                    # Also check for Ivan Dmitritx speech that follows
                    next_content2 = text[end:end+30]
                    if "Ivan Dm" in next_content2:
                        pass  # Don't remove - this is unique content
                    else:
                        pass
        text = text[:start] + text[end:]
        print("✓ Removed duplicate mental exam response")
else:
    print("✗ Could not find duplicate mental exam")

# 2j. Remove duplicate ## XI header and content
dup_xi = "## XI\nLa conversa va continuar"
if dup_xi in text:
    start = text.find(dup_xi)
    # Find end: the editing notes end before "—Mai no ens posarem"
    end_marker = "\n—Mai no ens posarem d'acord"
    end = text.find(end_marker, start)
    if end != -1:
        text = text[:start] + text[end:]
        print("✓ Removed duplicate XI header and editing notes")
else:
    print("✗ Could not find duplicate XI")

# 2k. Remove editing notes artifact (lines 293-297)
editing_notes = [
    '"Canviant \'durant hores senceres\' per \'hores senceres\' (més concís)"',
    '"Simplificant \'va procedir a buscar-lo\' per \'el va anar a buscar\'"',
    '"Naturalitzant \'cosa que mai no havia passat abans\' per \'fet que era totalment inèdit\'"',
    '"Reordenant \'el doctor gran havia anat a veure\' per \'el metge gran havia anat a visitar\'"',
    '"Canviant \'la conversa següent\' per \'aquesta conversa\' (més immediat)"'
]
for note in editing_notes:
    if note in text:
        text = text.replace(note + "\n", "")
        text = text.replace(note, "")

# Also try multi-line removal
editing_block = '''        "Canviant 'durant hores senceres' per 'hores senceres' (més concís)",
        "Simplificant 'va procedir a buscar-lo' per 'el va anar a buscar'",
        "Naturalitzant 'cosa que mai no havia passat abans' per 'fet que era totalment inèdit'",
        "Reordenant 'el doctor gran havia anat a veure' per 'el metge gran havia anat a visitar'",
        "Canviant 'la conversa següent' per 'aquesta conversa' (més immediat)"'''
if editing_block in text:
    text = text.replace(editing_block, "")
    print("✓ Removed editing notes artifact (block)")

# 2l. Remove JSON artifact line
json_artifact = '"Ievgueni Fiodòrovitx": "Ievgueni Fiodòrovitx"'
if json_artifact in text:
    text = text.replace(json_artifact + "\n", "")
    text = text.replace(json_artifact, "")
    print("✓ Removed JSON artifact")

# ===== 3. NAME STANDARDIZATION =====
# Order matters - do longer/more specific replacements first

# Andrei variants → Andrei Iefímitx
text = text.replace("Andréi Iefiмітx", "Andrei Iefímitx")  # Cyrillic fix
text = text.replace("Andrey Yefimitch", "Andrei Iefímitx")
text = text.replace("Andrey Yefímitx", "Andrei Iefímitx")
text = text.replace("Andrey Efímitx", "Andrei Iefímitx")
text = text.replace("Andrei Efímitx", "Andrei Iefímitx")
text = text.replace("Andrei Ièfimitx", "Andrei Iefímitx")

# Ivan variants → Ivan Dmítritx
text = text.replace("Ivan Dmítrïtx", "Ivan Dmítritx")
text = text.replace("Ivan Dmitrítx", "Ivan Dmítritx")
text = text.replace("Ivan Dmítritch", "Ivan Dmítritx")
text = text.replace("Ivan Dmitritch", "Ivan Dmítritx")
text = text.replace("Ivan Dmitrikh", "Ivan Dmítritx")
text = text.replace("Ivan Dmitritx", "Ivan Dmítritx")
# Note: "Ivan Dmítritx" is already correct, no change needed

# Mikhaïl variants → Mikhaïl Averiànitx
text = text.replace("Mihail Averyanitch", "Mikhaïl Averiànitx")
text = text.replace("Mihail Averiànitx", "Mikhaïl Averiànitx")
text = text.replace("Mikhaíl Averiànitx", "Mikhaïl Averiànitx")
text = text.replace("Mikhaïl Averianítx", "Mikhaïl Averiànitx")
text = text.replace("Mikhaïl Averiànytx", "Mikhaïl Averiànitx")
# "Mikhaïl Averiànitx" is already correct

# Dariúixka variants
text = text.replace("Dariuxka", "Dariúixka")
text = text.replace("Dariuixka", "Dariúixka")
text = text.replace("Darúixka", "Dariúixka")
# Handle "Darià" carefully - only in specific context
text = text.replace("Darià sortia", "Dariúixka sortia")
text = text.replace("la Darúixka", "la Dariúixka")

# Serguei variants → Serguei Serguéitx
text = text.replace("Serguei Sergueïtx", "Serguei Serguéitx")
text = text.replace("Serguei Serguèievitx", "Serguei Serguéitx")
text = text.replace("Serguei Serguéievitx", "Serguei Serguéitx")
text = text.replace("Sergei Serguèievitx", "Serguei Serguéitx")

# Moiseika/Moisseika
text = text.replace("Moisseika", "Moiseika")

# Hobotov/Khobótov - be careful not to change "Khobótov" which is correct
# First ensure Khobótov (with accent) stays
text = text.replace("Khobotov", "Khobótov")  # No accent → add accent
# Then change "Hobotov" (without Kh) to Khobótov
# But be careful: "Hobotov" should become "Khobótov"
# Do this only for standalone "Hobotov" not already part of "Khobótov"
# Simple approach: replace "Hobotov" then fix any double-Kh issues
text = text.replace("Hobotov", "Khobótov")
text = text.replace("KKhobótov", "Khobótov")  # Fix double replacement

# Ievgueni variants
text = text.replace("Ievgueni Fiòdorovitx", "Ievgueni Fiódorovitx")
text = text.replace("Ievgueni Fiodòrovitx", "Ievgueni Fiódorovitx")
text = text.replace("Ievgueni Fiodòritx", "Ievgueni Fiódorovitx")
text = text.replace("Yevgeny Fyodoritch", "Ievgueni Fiódorovitx")

# ===== 4. DIALOGUE FORMAT UNIFICATION =====
# Convert "quoted speech" to —em-dash format where it's clearly dialogue
# This is tricky - only convert clear speech patterns, not thoughts

# Convert thought patterns to «guillemets» consistently
# Patterns like "Text text" → «Text text»  (for thoughts)
# But some "quotes" are actual speech that should use em-dash

# Handle specific known problematic passages:

# Convert «guillemets» thoughts that use different formats:
# Pattern: 'text' (with typographic quotes used as thoughts)
# These are fine as-is if using «»

# Fix dialogue using "double quotes" for speech (should use —)
# The most reliable approach: fix known specific passages

# Lines where "text" is used for speech instead of —
# Fix the ones that use "text" for direct speech
# These are in the Warsaw/trip section and elsewhere

# Specific fixes for dialogue format:
speech_fixes = [
    ('"Això és vulgar," va dir', '—Això és vulgar —va dir'),
    ('"No entens que dius bestieses?"', '—No entens que dius bestieses?'),
    ('"Deixeu-me en pau," va cridar', '—Deixeu-me en pau! —va cridar'),
    ('"Fora, tots dos!" va continuar cridant', '—Fora, tots dos! —va continuar cridant'),
    ('"Estúpids! Ximples!', '—Estúpids! Ximples!'),
    ('No vull ni la teva amistat ni els teus medicaments, idiota! Vulgar! Repugnant!"',
     'No vull ni la teva amistat ni els teus medicaments, idiota! Vulgar! Repugnant!'),
    ('"Aneu-vos-en al diable!" va cridar', '—Aneu-vos-en al diable! —va cridar'),
    ('"Gent estúpida! Gent nècia!"', '«Gent estúpida! Gent nècia!»'),
    ('"No tornarem a pensar en el que ha passat"', '—No tornarem a pensar en el que ha passat'),
    ('"El passat, passat. Liubàvkin"', '—El passat, passat. Liubàvkin'),
    ('"No veus que estic ocupat? No recordarem el passat"', '—No veus que estic ocupat? No recordarem el passat'),
    ('"assegui\'s, li prego, estimat amic."', '—assegui\'s, li prego, estimat amic.'),
    ('"Això és vulgar,"', '—Això és vulgar —'),
]

for old, new in speech_fixes:
    text = text.replace(old, new)

# Fix thought patterns that use "double quotes" → «guillemets»
thought_patterns = [
    ('"Això és vulgar"', '«Això és vulgar»'),
    # General: lines starting with "text" that represent thoughts
]

# Convert remaining "double quotes" speech in specific blocks
# The trip/Warsaw section has many
text = text.replace(
    '"Fora, tots dos!" va cridar amb una veu que no semblava la seva',
    '—Fora, tots dos! —va cridar amb una veu que no semblava la seva'
)

# Fix mismatched quotes/format in specific dialogue passages
text = text.replace(
    '«Sí, está mentalment trastornat, però és un jove interessant.»',
    '—Sí, està mentalment trastornat, però és un jove interessant.'
)
text = text.replace(
    '«És hora que nosaltres, els vells, descancem!»',
    '—És hora que nosaltres, els vells, descancem!'
)

# ===== 5. FIX CYRILLIC CHARACTERS =====
# Any remaining Cyrillic
import unicodedata
def has_cyrillic(s):
    return any('CYRILLIC' in unicodedata.name(c, '') for c in s)

# Fix specific known Cyrillic issues
text = text.replace("Iefiмітx", "Iefímitx")

# ===== 6. CLEAN UP MULTIPLE BLANK LINES =====
while "\n\n\n\n" in text:
    text = text.replace("\n\n\n\n", "\n\n\n")
while "\n\n\n" in text:
    text = text.replace("\n\n\n", "\n\n")

# ===== 7. ADD CHAPTER XI HEADER =====
# Add ## XI before "Aviat es va saber per tot l'hospital"
xi_marker = "Aviat es va saber per tot l'hospital"
if xi_marker in text and "## XI\n" + xi_marker not in text and "## XI\nAviat" not in text:
    text = text.replace(xi_marker, "## XI\n" + xi_marker)
    print("✓ Added Chapter XI header")

# ===== VERIFY =====
print(f"\nOriginal length: {original_len}")
print(f"Fixed length: {len(text)}")
print(f"Removed: {original_len - len(text)} chars")

# Check for remaining Cyrillic
for i, line in enumerate(text.split('\n'), 1):
    if has_cyrillic(line):
        print(f"⚠ Cyrillic still found at line {i}: {line[:80]}")

# Check for remaining artifacts
if '`json' in text or '`\n' in text.replace('``', ''):
    print("⚠ Possible JSON artifact remaining")
if '"Canviant' in text or '"Simplificant' in text:
    print("⚠ Editing notes still present")

# Check name consistency
for variant in ["Andrey ", "Efímitx", "Dmitritch", "Dmitrikh", "Mihail ", "Moisseika",
                "Sergueïtx", "Serguèievitx", "Dariuxka", " Hobotov"]:
    if variant in text:
        idx = text.find(variant)
        context = text[max(0,idx-20):idx+40]
        print(f"⚠ Name variant still found: '{variant}' in: ...{context}...")

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)

print("\n✓ File written successfully")
