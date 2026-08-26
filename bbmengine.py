import os
import json
import glob
from datetime import datetime
from docx import Document
from google import genai
from google.genai import types

# 1. Inisialisasi API Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY tidak ditemukan!")

client = genai.Client(api_key=api_key)

# 2. Kelola State & Scanning Cerita Lama
STATE_FILE = "state.json"
STORIES_DIR = "stories"

# Buat folder stories jika belum ada
os.makedirs(STORIES_DIR, exist_ok=True)

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
else:
    state = {
        "generated_count": 0,
        "past_stories": []  # Menyimpan judul & tema cerita yang sudah dibuat
    }

# Ambil daftar cerita yang pernah dibuat
past_titles_str = ""
if state["past_stories"]:
    past_titles_str = "\n".join([f"- Judul: {item['title']} | Tema/Moral: {item['theme']}" for item in state["past_stories"]])
else:
    past_titles_str = "Belum ada cerita sebelumnya."

# 3. Susun Prompt Dongeng Anak (~1500 Kata + Anti-Pengulangan)
prompt = f"""
Kamu adalah seorang penulis dongeng anak-anak profesional dan berpengalaman.
Tugasmu adalah menulis 1 CERITA DONGENG ANAK LENGKAP (SEKALI FINISH) tanpa bab, tanpa bagian, dan tanpa episode.

Sangat Penting (Aturan Anti-Pengulangan):
Berikut adalah daftar judul/tema dongeng yang SUDAH PERNAH DIBUAT sebelumnya:
{past_titles_str}

JANGAN PERNAH membuat cerita yang mirip, menggunakan karakter utama yang sama, atau pesan moral yang serupa dengan daftar di atas! 
Ciptakan dunia dongeng, ide cerita, tokoh binatang/manusia, dan petualangan yang BENAR-BENAR BARU dan UNIK.

Kriteria Cerita:
1. Target Pembaca: Anak-anak (Bahasa seru, hangat, mendidik, dan santun).
2. Panjang Tulisan: Sekitar 1200 hingga 1500 kata. Tulislah cerita yang padat, imajinatif,mudah dipahami, dan dialog yang mengedukasi.
3. Pesan Moral: Memiliki pesan moral yang baik di akhir cerita.
4. Format Output: 
   - Baris pertama HARUS berupa Judul Dongeng (Tanpa tanda baca aneh atau kata 'Judul:').
   - Baris berikutnya langsung masuk ke isi cerita penuh sampai selesai.
"""

print("Generating Dongeng Anak Baru...")

# 4. Panggil Gemini (Menggunakan gemini-2.5-flash)
response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        temperature=0.9, # Temperature sedikit tinggi agar ide bervariasi
    )
)

full_text = response.text.strip()

# Separasi Judul dan Isi Cerita
lines = full_text.split("\n", 1)
story_title = lines[0].replace("#", "").strip()
story_content = lines[1].strip() if len(lines) > 1 else ""

print(f"Judul Tercipta: {story_title}")

# 5. Simpan Hasil ke Format .docx di Folder 'stories'
# Buat nama file aman dari karakter aneh
safe_title = "".join(c for c in story_title if c.isalnum() or c in (" ", "_", "-")).rstrip()
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
docx_filename = os.path.join(STORIES_DIR, f"{timestamp}_{safe_title}.docx")

doc = Document()
doc.add_heading(story_title, level=1)

# Tambahkan paragraf demi paragraf
for paragraph in story_content.split("\n\n"):
    clean_p = paragraph.strip()
    if clean_p:
        doc.add_paragraph(clean_p)

doc.save(docx_filename)
print(f"File tersimpan di: {docx_filename}")

# 6. Dapatkan Rangkuman Singkat untuk Memory State
summary_prompt = f"Rangkum dalam 1 kalimat tema utama dan pesan moral dari dongeng ini:\n\n{story_content[:1000]}"
summary_response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=summary_prompt
)

# 7. Update State File
state["generated_count"] += 1
state["past_stories"].append({
    "title": story_title,
    "theme": summary_response.text.strip(),
    "file": docx_filename,
    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
})

with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

print(f"State berhasil diperbarui. Total cerita: {state['generated_count']}")