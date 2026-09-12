with open('scratch/seal_base64.txt', 'r') as f:
    b64 = f.read().strip()

with open('letters/letters.js', 'r', encoding='utf-8') as f:
    content = f.read()

header = f'''// =========================================================================
// NEBBIE'S LETTERS ARCHIVE (Source of Truth)
// Generated and managed by The Wax & Quill Studio (letters/index.html)
// =========================================================================

window.SWAN_SEAL_B64 = "{b64}";

'''

idx = content.find('window.LOVE_LETTERS')
new_content = header + content[idx:]
with open('letters/letters.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Updated letters/letters.js successfully!')

