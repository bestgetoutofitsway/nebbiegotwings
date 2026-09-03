"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              THE VINYL VAULT · AUTOMATED RECORD PRESSING STUDIO              ║
║  Native Desktop Studio with Automatic Local File Saving (Audio & Covers)     ║
║  Always copies audio to assets/songX.mp3 & covers to assets/coverX.jpg       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import re
import sys
import shutil
import json
import struct
import base64
import urllib.request
import urllib.parse
import tkinter as tk
from tkinter import filedialog, messagebox

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(WORKSPACE_DIR, 'assets')
VAULT_PATH = os.path.join(WORKSPACE_DIR, 'vault.html')
INDEX_PATH = os.path.join(WORKSPACE_DIR, 'index.html')

os.makedirs(ASSETS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# PURE PYTHON IMAGE DIMENSION READER
# ---------------------------------------------------------------------------
def get_image_dimensions(file_path):
    try:
        with open(file_path, 'rb') as f:
            head = f.read(32)
            if head.startswith(b'\x89PNG\r\n\x1a\n'):
                w, h = struct.unpack('>II', head[16:24])
                return w, h
            elif head.startswith(b'GIF87a') or head.startswith(b'GIF89a'):
                w, h = struct.unpack('<HH', head[6:10])
                return w, h
            elif head.startswith(b'RIFF') and head[8:12] == b'WEBP':
                f.seek(12)
                chunk = f.read(18)
                if chunk.startswith(b'VP8 '):
                    w, h = struct.unpack('<HH', chunk[14:18])
                    return w & 0x3fff, h & 0x3fff
                elif chunk.startswith(b'VP8X'):
                    w = int.from_bytes(chunk[12:15], 'little') + 1
                    h = int.from_bytes(chunk[15:18], 'little') + 1
                    return w, h
            elif head.startswith(b'\xff\xd8'): # JPEG
                f.seek(0)
                f.read(2)
                b = f.read(1)
                while b and b != b'':
                    while b != b'\xff':
                        b = f.read(1)
                    while b == b'\xff':
                        b = f.read(1)
                    if b and b[0] in [0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF]:
                        f.read(3)
                        h, w = struct.unpack('>HH', f.read(4))
                        return w, h
                    else:
                        len_bytes = f.read(2)
                        if len(len_bytes) < 2:
                            break
                        l = struct.unpack('>H', len_bytes)[0]
                        f.seek(l - 2, 1)
                    b = f.read(1)
    except Exception:
        pass
    return None, None

# ---------------------------------------------------------------------------
# METADATA & ARTWORK SEARCH HELPERS
# ---------------------------------------------------------------------------
def fetch_itunes_artwork(query):
    try:
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=4"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as res:
            data = json.loads(res.read().decode('utf-8'))
            for item in data.get('results', []):
                art = item.get('artworkUrl100', '')
                if art:
                    high_res = art.replace('100x100bb', '1000x1000bb')
                    return {
                        'title': item.get('trackName', ''),
                        'artist': item.get('artistName', ''),
                        'album': item.get('collectionName', ''),
                        'cover': high_res
                    }
    except Exception:
        pass
    return None

def extract_audio_tags(file_path):
    title = os.path.splitext(os.path.basename(file_path))[0]
    artist = "Unknown Artist"

    clean_name = re.sub(r'^\d+\s*[-_.]\s*', '', title)
    if ' - ' in clean_name:
        parts = clean_name.split(' - ', 1)
        artist = parts[0].strip()
        title = parts[1].strip()
    else:
        title = clean_name.replace('_', ' ').title()

    return title, artist

def generate_palette(seed_str=""):
    palettes = [
        {
            'nebula1': 'rgba(219, 39, 119, 0.18)', 'nebula2': 'rgba(126, 34, 206, 0.14)',
            'starAccent': {'r': 244, 'g': 114, 'b': 182}, 'glow': 'rgba(236, 72, 153, 0.45)',
            'stageShadow': 'rgba(236, 72, 153, 0.45)', 'fallbackCover': 'linear-gradient(135deg, #4a044e, #1e1b4b)'
        },
        {
            'nebula1': 'rgba(76, 29, 149, 0.18)', 'nebula2': 'rgba(219, 39, 119, 0.15)',
            'starAccent': {'r': 192, 'g': 132, 'b': 252}, 'glow': 'rgba(168, 85, 247, 0.45)',
            'stageShadow': 'rgba(168, 85, 247, 0.45)', 'fallbackCover': 'linear-gradient(135deg, #1e1b4b, #3b0764)'
        },
        {
            'nebula1': 'rgba(202, 138, 4, 0.15)', 'nebula2': 'rgba(131, 24, 67, 0.16)',
            'starAccent': {'r': 254, 'g': 240, 'b': 138}, 'glow': 'rgba(234, 179, 8, 0.35)',
            'stageShadow': 'rgba(234, 179, 8, 0.35)', 'fallbackCover': 'linear-gradient(135deg, #713f12, #450a0a)'
        },
        {
            'nebula1': 'rgba(225, 29, 72, 0.18)', 'nebula2': 'rgba(88, 28, 135, 0.14)',
            'starAccent': {'r': 251, 'g': 113, 'b': 133}, 'glow': 'rgba(225, 29, 72, 0.35)',
            'stageShadow': 'rgba(225, 29, 72, 0.35)', 'fallbackCover': 'linear-gradient(135deg, #881337, #2e1065)'
        },
        {
            'nebula1': 'rgba(13, 148, 136, 0.16)', 'nebula2': 'rgba(124, 58, 237, 0.14)',
            'starAccent': {'r': 45, 'g': 212, 'b': 191}, 'glow': 'rgba(20, 184, 166, 0.35)',
            'stageShadow': 'rgba(20, 184, 166, 0.35)', 'fallbackCover': 'linear-gradient(135deg, #134e4a, #311042)'
        }
    ]
    idx = sum(ord(c) for c in seed_str) % len(palettes)
    return palettes[idx]

# ---------------------------------------------------------------------------
# AUTOMATED CODE & FILE INSERTION (ALWAYS LOCAL ASSETS)
# ---------------------------------------------------------------------------
def press_record(audio_file, custom_title=None, custom_artist=None, custom_note=None, custom_cover_file=None, custom_cover_url=None):
    if audio_file and not os.path.isfile(audio_file):
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    inferred_title, inferred_artist = extract_audio_tags(audio_file) if audio_file else ("Untitled Track", "Unknown Artist")
    title = (custom_title or inferred_title).strip()
    artist = (custom_artist or inferred_artist).strip()
    note = (custom_note or "").strip()

    # 1. Determine next available slot in assets/
    existing_songs = [f for f in os.listdir(ASSETS_DIR) if f.startswith('song') and f.endswith('.mp3')]
    song_nums = []
    for s in existing_songs:
        m = re.search(r'song(\d+)\.mp3', s)
        if m:
            song_nums.append(int(m.group(1)))
    next_num = (max(song_nums) + 1) if song_nums else 1
    dest_audio_name = f"song{next_num}.mp3"
    dest_audio_path = os.path.join(ASSETS_DIR, dest_audio_name)

    # Copy audio file to assets/
    if audio_file and os.path.isfile(audio_file):
        shutil.copy2(audio_file, dest_audio_path)
    relative_audio_src = f"assets/{dest_audio_name}"

    # 2. ALWAYS save cover image locally to assets/coverX.jpg
    dest_cover_name = f"cover{next_num}.jpg"
    dest_cover_path = os.path.join(ASSETS_DIR, dest_cover_name)
    cover_url = f"assets/{dest_cover_name}"

    if custom_cover_file and os.path.isfile(custom_cover_file):
        # Local custom image file -> Copy to assets/coverX.jpg
        shutil.copy2(custom_cover_file, dest_cover_path)
    elif custom_cover_url:
        if custom_cover_url.startswith('data:image'):
            # Base64 string -> Decode to assets/coverX.jpg
            header, b64data = custom_cover_url.split(',', 1)
            with open(dest_cover_path, 'wb') as img_f:
                img_f.write(base64.b64decode(b64data))
        elif custom_cover_url.startswith('http'):
            # Remote URL -> Download to assets/coverX.jpg
            try:
                req = urllib.request.Request(custom_cover_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=8) as resp, open(dest_cover_path, 'wb') as out_f:
                    shutil.copyfileobj(resp, out_f)
            except Exception:
                cover_url = custom_cover_url
        else:
            cover_url = custom_cover_url
    else:
        # Query Apple Music -> Download 1000x1000 cover to assets/coverX.jpg
        itunes_info = fetch_itunes_artwork(f"{title} {artist}")
        if itunes_info and itunes_info.get('cover'):
            try:
                req = urllib.request.Request(itunes_info['cover'], headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=8) as resp, open(dest_cover_path, 'wb') as out_f:
                    shutil.copyfileobj(resp, out_f)
            except Exception:
                cover_url = itunes_info['cover']

    pal = generate_palette(title + artist)

    with open(VAULT_PATH, 'r', encoding='utf-8') as f:
        vault_code = f.read()

    existing_ids = [int(m) for m in re.findall(r'id:\s*(\d+)', vault_code)]
    new_id = (max(existing_ids) + 1) if existing_ids else next_num
    badge_str = f"Track {new_id:02d}"

    new_vault_track_obj = f"""      {{ 
        id: {new_id}, title: {json.dumps(title)}, artist: {json.dumps(artist)}, src: '{relative_audio_src}', 
        note: {json.dumps(note)}, badge: '{badge_str}', 
        cover: '{cover_url}',
        fallbackCover: '{pal['fallbackCover']}',
        palette: {{
          nebula1: '{pal['nebula1']}', nebula2: '{pal['nebula2']}',
          starAccent: {{ r: {pal['starAccent']['r']}, g: {pal['starAccent']['g']}, b: {pal['starAccent']['b']} }}, glow: '{pal['glow']}',
          stageShadow: '{pal['stageShadow']}'
        }}
      }}"""

    vault_pl_match = re.search(r'const playlist = \[\s*([\s\S]*?)\n\s*\];', vault_code)
    if vault_pl_match:
        old_array_body = vault_pl_match.group(1)
        new_array_body = old_array_body.rstrip() + ",\n" + new_vault_track_obj
        vault_code = vault_code.replace(old_array_body, new_array_body, 1)

        vault_code = re.sub(
            r"(trackIds:\s*\[[\d,\s]+)\]",
            rf"\g<1>, {new_id}]",
            vault_code,
            count=1
        )

        vault_code = re.sub(r'(\d+)\s+Pressings', f"{new_id} Pressings", vault_code)
        vault_code = re.sub(r'·\s*(\d+)\s*Tracks', f"· {new_id} Tracks", vault_code)

        with open(VAULT_PATH, 'w', encoding='utf-8') as f:
            f.write(vault_code)

    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        index_code = f.read()

    new_index_track_obj = f"""    {{
      title: {json.dumps(title)},
      artist: {json.dumps(artist)},
      src: "{relative_audio_src}",
      cover: "{cover_url}"
    }}"""

    index_pl_match = re.search(r'const playlist = \[\s*([\s\S]*?)\n\s*\];', index_code)
    if index_pl_match:
        old_idx_body = index_pl_match.group(1)
        new_idx_body = old_idx_body.rstrip() + ",\n" + new_index_track_obj
        index_code = index_code.replace(old_idx_body, new_idx_body, 1)

        with open(INDEX_PATH, 'w', encoding='utf-8') as f:
            f.write(index_code)

    return {
        'id': new_id,
        'title': title,
        'artist': artist,
        'badge': badge_str,
        'src': relative_audio_src,
        'cover': cover_url or pal['fallbackCover']
    }

def apply_pasted_track_code(code_text, audio_file_path=None):
    title_match = re.search(r'title:\s*["\'](.*?)["\']', code_text)
    artist_match = re.search(r'artist:\s*["\'](.*?)["\']', code_text)
    note_match = re.search(r'note:\s*["\'](.*?)["\']', code_text)
    cover_match = re.search(r'cover:\s*["\'](.*?)["\']', code_text, re.DOTALL)

    title = title_match.group(1) if title_match else "Untitled Track"
    artist = artist_match.group(1) if artist_match else "Unknown Artist"
    note = note_match.group(1) if note_match else ""
    cover = cover_match.group(1) if cover_match else ""

    return press_record(audio_file_path, custom_title=title, custom_artist=artist, custom_note=note, custom_cover_url=cover)

# ---------------------------------------------------------------------------
# NATIVE DESKTOP TKINTER STUDIO
# ---------------------------------------------------------------------------
class VaultStudioDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("The Vinyl Vault · Record Pressing Studio")
        self.root.geometry("680x840")
        self.root.minsize(620, 760)
        self.root.configure(bg="#0d020a")

        self.audio_path = tk.StringVar()
        self.cover_path = tk.StringVar()
        self.title_var = tk.StringVar()
        self.artist_var = tk.StringVar()
        self.note_var = tk.StringVar()
        self.art_status_var = tk.StringVar(value="(auto-fetch 1000x1000 enabled)")
        self.dimension_badge_var = tk.StringVar(value="Target: 1000 × 1000 px (1:1 Square)")

        self.paster_audio_path = tk.StringVar()

        self.build_ui()

    def build_ui(self):
        # Header Banner
        header = tk.Frame(self.root, bg="#1a0413", padx=20, pady=12, highlightbackground="#ec4899", highlightthickness=1)
        header.pack(fill="x", padx=16, pady=(14, 8))

        top_row = tk.Frame(header, bg="#1a0413")
        top_row.pack(fill="x")
        tk.Label(top_row, text="💿 THE VINYL PRESSING STUDIO", font=("Georgia", 14, "bold"), fg="#ffd6e0", bg="#1a0413").pack(side="left")
        tk.Label(top_row, text="● Auto-Assets Engine Ready", font=("Consolas", 8, "bold"), fg="#34d399", bg="#1a0413").pack(side="right")
        
        tk.Label(header, text="Direct Hard Drive Automation · Saves Audio & Covers to assets/", font=("Consolas", 9), fg="#f472b6", bg="#1a0413").pack(anchor="w", pady=(2, 0))

        # Mode Selector Tabs
        tab_bar = tk.Frame(self.root, bg="#0d020a")
        tab_bar.pack(fill="x", padx=16, pady=(4, 8))

        self.btn_tab_visual = tk.Button(tab_bar, text="✨ 1. Visual Record Ingestion", command=self.show_visual_tab, font=("Consolas", 9, "bold"), bg="#be123c", fg="#ffffff", activebackground="#ec4899", relief="flat", padx=14, pady=6, cursor="hand2")
        self.btn_tab_visual.pack(side="left", padx=(0, 6))

        self.btn_tab_paster = tk.Button(tab_bar, text="📋 2. Paste Track Code & Auto-Apply", command=self.show_paster_tab, font=("Consolas", 9, "bold"), bg="#1f0617", fg="#ffd6e0", activebackground="#ec4899", relief="flat", padx=14, pady=6, cursor="hand2")
        self.btn_tab_paster.pack(side="left")

        # Container Frames for Tabs
        self.visual_frame = tk.Frame(self.root, bg="#0d020a", padx=16)
        self.visual_frame.pack(fill="both", expand=True)

        self.paster_frame = tk.Frame(self.root, bg="#0d020a", padx=16)

        # BUILD VISUAL TAB
        self.build_visual_tab()

        # BUILD PASTER TAB
        self.build_paster_tab()

    def build_visual_tab(self):
        # 1. Audio File Section
        self.create_field(self.visual_frame, "1. Drag & Drop or Select Audio File (.mp3, .wav, .m4a):", self.audio_path, self.browse_audio, btn_text="Select Audio")

        # 2. Track Metadata
        meta_box = tk.LabelFrame(self.visual_frame, text=" 2. Track Metadata ", font=("Consolas", 10, "bold"), fg="#f472b6", bg="#160512", padx=14, pady=8, highlightbackground="#3d0e2c", highlightthickness=1)
        meta_box.pack(fill="x", pady=8)

        tk.Label(meta_box, text="Song Title:", font=("Consolas", 9, "bold"), fg="#ffd6e0", bg="#160512").grid(row=0, column=0, sticky="w", pady=3)
        tk.Entry(meta_box, textvariable=self.title_var, font=("Segoe UI", 10), bg="#0d020a", fg="#ffffff", insertbackground="#ec4899", relief="flat", highlightbackground="#ec4899", highlightthickness=1).grid(row=0, column=1, sticky="ew", padx=8, pady=3)

        tk.Label(meta_box, text="Artist Name:", font=("Consolas", 9, "bold"), fg="#ffd6e0", bg="#160512").grid(row=1, column=0, sticky="w", pady=3)
        tk.Entry(meta_box, textvariable=self.artist_var, font=("Segoe UI", 10), bg="#0d020a", fg="#ffffff", insertbackground="#ec4899", relief="flat", highlightbackground="#ec4899", highlightthickness=1).grid(row=1, column=1, sticky="ew", padx=8, pady=3)

        tk.Label(meta_box, text="Memory Note (optional):", font=("Consolas", 9), fg="#ffd6e0", bg="#160512").grid(row=2, column=0, sticky="w", pady=3)
        tk.Entry(meta_box, textvariable=self.note_var, font=("Segoe UI", 10), bg="#0d020a", fg="#ffffff", insertbackground="#ec4899", relief="flat", highlightbackground="#3d0e2c", highlightthickness=1).grid(row=2, column=1, sticky="ew", padx=8, pady=3)

        meta_box.columnconfigure(1, weight=1)

        # 3. Artwork Section
        art_box = tk.LabelFrame(self.visual_frame, text=" 3. Album Cover Artwork (Target: 1000 × 1000 px) ", font=("Consolas", 10, "bold"), fg="#f472b6", bg="#160512", padx=14, pady=8, highlightbackground="#3d0e2c", highlightthickness=1)
        art_box.pack(fill="x", pady=8)

        self.create_sub_field(art_box, "Custom Image (for unreleased songs):", self.cover_path, self.browse_cover)

        # Live Fit & Status Banner
        status_box = tk.Frame(art_box, bg="#0d020a", padx=10, pady=6, highlightbackground="#3d0e2c", highlightthickness=1)
        status_box.pack(fill="x", pady=(6, 4))
        
        self.badge_lbl = tk.Label(status_box, textvariable=self.dimension_badge_var, font=("Consolas", 9, "bold"), fg="#34d399", bg="#0d020a")
        self.badge_lbl.pack(anchor="w")

        self.status_lbl = tk.Label(status_box, textvariable=self.art_status_var, font=("Consolas", 8, "italic"), fg="#f472b6", bg="#0d020a")
        self.status_lbl.pack(anchor="w", pady=(2, 0))

        # Auto search button
        fetch_btn = tk.Button(art_box, text="🔍 Test Auto-Fetch Official 1000x1000 Artwork from Apple Music", command=self.test_artwork_fetch, font=("Consolas", 9), bg="#2d0822", fg="#ffd6e0", activebackground="#ec4899", activeforeground="#ffffff", relief="flat", padx=10, pady=4, cursor="hand2")
        fetch_btn.pack(pady=(4, 2), anchor="w")

        # 4. Action Button
        press_btn = tk.Button(self.visual_frame, text="💿 PRESS RECORD INTO THE VAULT", command=self.on_press_click, font=("Georgia", 12, "bold"), bg="#be123c", fg="#ffffff", activebackground="#ec4899", activeforeground="#ffffff", relief="flat", padx=20, pady=12, cursor="hand2", highlightbackground="#f43f5e", highlightthickness=1)
        press_btn.pack(fill="x", pady=(10, 14))

    def build_paster_tab(self):
        paste_card = tk.LabelFrame(self.paster_frame, text=" Paste Track Code Snippet ", font=("Consolas", 10, "bold"), fg="#f472b6", bg="#160512", padx=16, pady=12, highlightbackground="#3d0e2c", highlightthickness=1)
        paste_card.pack(fill="both", expand=True, pady=10)

        # Optional MP3 Selector in Paster Tab
        tk.Label(paste_card, text="1. Select Matching MP3 File (Copies to assets/ automatically):", font=("Consolas", 9, "bold"), fg="#ffd6e0", bg="#160512").pack(anchor="w", pady=(0, 2))
        audio_row = tk.Frame(paste_card, bg="#160512")
        audio_row.pack(fill="x", pady=(0, 8))
        tk.Entry(audio_row, textvariable=self.paster_audio_path, font=("Segoe UI", 9), bg="#000000", fg="#ffffff", insertbackground="#ec4899", relief="flat", highlightbackground="#3d0e2c", highlightthickness=1).pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Button(audio_row, text="Select MP3", command=self.browse_paster_audio, font=("Consolas", 9, "bold"), bg="#be123c", fg="#ffffff", activebackground="#ec4899", relief="flat", padx=12, pady=3, cursor="hand2").pack(side="right")

        tk.Label(paste_card, text="2. Paste Track Object Code:", font=("Consolas", 9, "bold"), fg="#ffd6e0", bg="#160512").pack(anchor="w", pady=(0, 4))

        self.code_text_box = tk.Text(paste_card, height=10, wrap="none", bg="#0d020a", fg="#ffd6e0", insertbackground="#ec4899", relief="flat", highlightbackground="#ec4899", highlightthickness=1, font=("Consolas", 9))
        self.code_text_box.pack(fill="both", expand=True, pady=(0, 10))

        apply_btn = tk.Button(paste_card, text="⚡ AUTO-APPLY PASTED CODE & SAVE TO ASSETS", command=self.on_apply_pasted_code, font=("Georgia", 11, "bold"), bg="#be123c", fg="#ffffff", activebackground="#ec4899", relief="flat", padx=20, pady=10, cursor="hand2")
        apply_btn.pack(fill="x")

        self.paster_status_lbl = tk.Label(paste_card, text="", font=("Consolas", 9, "bold"), fg="#34d399", bg="#160512")
        self.paster_status_lbl.pack(pady=(6, 0))

    def show_visual_tab(self):
        self.paster_frame.pack_forget()
        self.visual_frame.pack(fill="both", expand=True)
        self.btn_tab_visual.config(bg="#be123c", fg="#ffffff")
        self.btn_tab_paster.config(bg="#1f0617", fg="#ffd6e0")

    def show_paster_tab(self):
        self.visual_frame.pack_forget()
        self.paster_frame.pack(fill="both", expand=True)
        self.btn_tab_paster.config(bg="#be123c", fg="#ffffff")
        self.btn_tab_visual.config(bg="#1f0617", fg="#ffd6e0")

    def create_field(self, parent, label, var, cmd, btn_text="Browse"):
        f = tk.Frame(parent, bg="#0d020a")
        f.pack(fill="x", pady=3)
        tk.Label(f, text=label, font=("Consolas", 9, "bold"), fg="#ffd6e0", bg="#0d020a").pack(anchor="w")
        row = tk.Frame(f, bg="#0d020a")
        row.pack(fill="x", pady=(2, 0))
        entry = tk.Entry(row, textvariable=var, font=("Segoe UI", 9), bg="#000000", fg="#ffffff", insertbackground="#ec4899", relief="flat", highlightbackground="#3d0e2c", highlightthickness=1)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        btn = tk.Button(row, text=btn_text, command=cmd, font=("Consolas", 9, "bold"), bg="#be123c", fg="#ffffff", activebackground="#ec4899", relief="flat", padx=12, pady=3, cursor="hand2")
        btn.pack(side="right")

    def create_sub_field(self, parent, label, var, cmd):
        tk.Label(parent, text=label, font=("Consolas", 9), fg="#ffd6e0", bg="#160512").pack(anchor="w")
        row = tk.Frame(parent, bg="#160512")
        row.pack(fill="x", pady=(2, 0))
        entry = tk.Entry(row, textvariable=var, font=("Segoe UI", 9), bg="#000000", fg="#ffffff", insertbackground="#ec4899", relief="flat", highlightbackground="#3d0e2c", highlightthickness=1)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        btn = tk.Button(row, text="Select Image", command=cmd, font=("Consolas", 8), bg="#3d0e2c", fg="#ffd6e0", activebackground="#ec4899", relief="flat", padx=8, pady=2, cursor="hand2")
        btn.pack(side="right")

    def browse_audio(self):
        f = filedialog.askopenfilename(title="Select Audio File", filetypes=[("Audio Files", "*.mp3 *.wav *.m4a *.aac *.ogg"), ("All Files", "*.*")])
        if f:
            self.audio_path.set(f)
            t, a = extract_audio_tags(f)
            if not self.title_var.get(): self.title_var.set(t)
            if not self.artist_var.get() or self.artist_var.get() == "Unknown Artist": self.artist_var.set(a)
            self.test_artwork_fetch()

    def browse_paster_audio(self):
        f = filedialog.askopenfilename(title="Select Audio File", filetypes=[("Audio Files", "*.mp3 *.wav *.m4a *.aac *.ogg"), ("All Files", "*.*")])
        if f:
            self.paster_audio_path.set(f)

    def browse_cover(self):
        f = filedialog.askopenfilename(title="Select Custom Cover Image (1000x1000 recommended)", filetypes=[("Image Files", "*.jpg *.jpeg *.png *.webp *.avif"), ("All Files", "*.*")])
        if f:
            self.cover_path.set(f)
            self.validate_image_fit(f)

    def validate_image_fit(self, file_path):
        w, h = get_image_dimensions(file_path)
        base = os.path.basename(file_path)

        if w and h:
            is_square = abs(w - h) <= 2
            if is_square and w >= 800:
                self.dimension_badge_var.set(f"✅ PERFECT 1:1 FIT: {w} × {h} px (Square)")
                self.badge_lbl.config(fg="#34d399")
                self.art_status_var.set(f"Loaded: {base} (Crisp on turntable & crate)")
            elif is_square:
                self.dimension_badge_var.set(f"✅ 1:1 Square ({w} × {h} px) — Fits nicely!")
                self.badge_lbl.config(fg="#6ee7b7")
                self.art_status_var.set(f"Loaded: {base}")
            else:
                self.dimension_badge_var.set(f"⚠️ NOT A SQUARE: {w} × {h} px (Rectangular)")
                self.badge_lbl.config(fg="#f59e0b")
                self.art_status_var.set(f"Loaded: {base} (Will auto-center on vinyl sleeve)")
        else:
            self.dimension_badge_var.set("ℹ Custom Image Selected")
            self.badge_lbl.config(fg="#f472b6")
            self.art_status_var.set(f"Loaded: {base}")

    def test_artwork_fetch(self):
        t = self.title_var.get()
        a = self.artist_var.get()
        if not t: return
        self.art_status_var.set("Searching Apple Music CDN for 1000x1000 artwork...")
        self.root.update()
        info = fetch_itunes_artwork(f"{t} {a}")
        if info and info.get('cover'):
            self.dimension_badge_var.set("✅ Official Apple Master Artwork: 1000 × 1000 px ✓")
            self.badge_lbl.config(fg="#34d399")
            self.art_status_var.set(f"✓ Found Official Artwork for {info.get('album', t)} (Will auto-save to assets/)")
        else:
            self.art_status_var.set("ℹ No online cover found (using ambient celestial gradient or custom image)")

    def on_press_click(self):
        audio = self.audio_path.get().strip()
        if not audio or not os.path.isfile(audio):
            messagebox.showerror("Missing File", "Please select a valid audio (.mp3) file.")
            return

        t = self.title_var.get().strip()
        a = self.artist_var.get().strip()
        n = self.note_var.get().strip()
        c = self.cover_path.get().strip()

        try:
            result = press_record(audio, custom_title=t, custom_artist=a, custom_note=n, custom_cover_file=c)
            messagebox.showinfo(
                "Record Pressed!",
                f"✨ Successfully Pressed into the Vault!\n\n"
                f"Track ID: {result['badge']}\n"
                f"Title: {result['title']}\n"
                f"Artist: {result['artist']}\n"
                f"Audio: {result['src']}\n"
                f"Cover: {result['cover']}\n\n"
                f"Both audio and artwork have been saved to assets/ automatically!"
            )
            self.audio_path.set("")
            self.cover_path.set("")
            self.title_var.set("")
            self.artist_var.set("")
            self.note_var.set("")
            self.dimension_badge_var.set("Target: 1000 × 1000 px (1:1 Square)")
            self.badge_lbl.config(fg="#34d399")
            self.art_status_var.set("(ready for next record)")
        except Exception as err:
            messagebox.showerror("Error", f"Failed to press record: {err}")

    def on_apply_pasted_code(self):
        code = self.code_text_box.get("1.0", tk.END).strip()
        if not code:
            messagebox.showerror("Missing Code", "Please paste your track code snippet into the box first.")
            return

        audio_p = self.paster_audio_path.get().strip()
        if audio_p and not os.path.isfile(audio_p):
            audio_p = None

        try:
            res = apply_pasted_track_code(code, audio_file_path=audio_p)
            self.paster_status_lbl.config(text=f"✓ Successfully Applied {res['badge']}: '{res['title']}' into Vault & Index!", fg="#34d399")
            messagebox.showinfo("Applied!", f"✨ Successfully Applied {res['badge']}: '{res['title']}' by {res['artist']} to the website!\n\nAudio and Artwork saved to assets/ automatically.")
            self.code_text_box.delete("1.0", tk.END)
            self.paster_audio_path.set("")
        except Exception as err:
            self.paster_status_lbl.config(text=f"Error: {err}", fg="#ef4444")
            messagebox.showerror("Error", f"Failed to apply track code: {err}")

# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        file_arg = sys.argv[1]
        print(f"[Vinyl Vault Pressing Studio] Pressing: {file_arg}")
        res = press_record(file_arg)
        print(f"SUCCESS: pressed {res['badge']}: {res['title']} by {res['artist']} into vault.html & index.html!")
    else:
        root = tk.Tk()
        app = VaultStudioDesktopApp(root)
        root.mainloop()
