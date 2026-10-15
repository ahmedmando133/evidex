import os
import shutil
import subprocess
from pathlib import Path

DOSSIER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DOSSIER_DIR.parent
ARTIFACT_DIR = Path(r"C:\Users\Mando\.gemini\antigravity\brain\15684f81-3661-4ee4-ac9e-9e2058e52711")

CHROME_BIN = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_BIN):
    CHROME_BIN = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

SVG_EMBLEM = """<svg width="76" height="58" viewBox="0 0 120 90" fill="none" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 0 14px rgba(0, 245, 212, 0.55)) drop-shadow(0 0 20px rgba(168, 85, 247, 0.45));">
  <defs>
    <linearGradient id="m_ribbon_left" x1="15%" y1="90%" x2="55%" y2="10%">
      <stop offset="0%" stop-color="#00F5D4"/>
      <stop offset="60%" stop-color="#00BBF9"/>
      <stop offset="100%" stop-color="#38BDF8"/>
    </linearGradient>
    <linearGradient id="m_ribbon_right" x1="45%" y1="10%" x2="85%" y2="90%">
      <stop offset="0%" stop-color="#38BDF8"/>
      <stop offset="35%" stop-color="#6366F1"/>
      <stop offset="75%" stop-color="#8B5CF6"/>
      <stop offset="100%" stop-color="#A855F7"/>
    </linearGradient>
    <linearGradient id="m_ribbon_glow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2DD4BF"/>
      <stop offset="100%" stop-color="#C084FC"/>
    </linearGradient>
  </defs>
  <path d="M 28 74 C 20 54 26 24 46 18 C 58 14 65 30 58 56" stroke="url(#m_ribbon_left)" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M 62 56 C 55 30 62 14 74 18 C 94 24 100 54 92 74" stroke="url(#m_ribbon_right)" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M 46 20 C 58 28 62 46 60 56" stroke="url(#m_ribbon_glow)" stroke-width="10" stroke-linecap="round" fill="none" opacity="0.95"/>
</svg>"""

def update_all():
    print("=" * 60)
    print("[UPDATE] Updating MANDOROS Platform Specification Dossier & PDF...")
    print("=" * 60)

    html_file = DOSSIER_DIR / "mandoros_dossier.html"
    scratch_file = Path(r"C:\Users\Mando\.gemini\antigravity\brain\15684f81-3661-4ee4-ac9e-9e2058e52711\scratch\mandoros_dossier.html")
    
    if scratch_file.exists():
        shutil.copy2(scratch_file, html_file)
    
    pdf_out_dossier = DOSSIER_DIR / "MANDOROS_Platform_Specification_Dossier.pdf"
    pdf_out_root = PROJECT_ROOT / "MANDOROS_Platform_Specification_Dossier.pdf"
    pdf_out_artifact = ARTIFACT_DIR / "MANDOROS_Platform_Specification_Dossier.pdf"

    cmd = [
        CHROME_BIN,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={str(pdf_out_dossier)}",
        str(html_file.resolve())
    ]
    subprocess.run(cmd, check=True)
    shutil.copy2(pdf_out_dossier, pdf_out_root)
    if ARTIFACT_DIR.exists():
        shutil.copy2(pdf_out_dossier, pdf_out_artifact)

    print(f"[OK] Dossier PDF successfully generated: {pdf_out_dossier.name} ({pdf_out_dossier.stat().st_size:,} bytes)")
    print(f"[OK] Synchronized across project root and conversation artifacts.")

if __name__ == "__main__":
    update_all()
