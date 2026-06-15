"""Generate messy-but-realistic sample medical documents for the vision demo.

Renders Indian-style prescription / hospital-bill / pharmacy-bill images with
Pillow (per `sample_documents_guide.md`) into `samples/`, plus a heavily blurred
"phone photo" bill to exercise the unreadable-document gate.

Usage:
    .venv/bin/python scripts/make_sample_docs.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "samples"

# Try a few common macOS/Linux font paths; fall back to PIL's bitmap font.
_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _render(lines: list[tuple[str, int]], width: int = 920) -> Image.Image:
    """Render (text, size) lines top-to-bottom onto a white page."""
    height = 80 + sum(size + 14 for _, size in lines)
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    y = 40
    for text, size in lines:
        draw.text((50, y), text, fill=(15, 15, 15), font=_font(size))
        y += size + 14
    # A thin border so it reads as a document.
    draw.rectangle([(12, 12), (width - 12, height - 12)], outline=(120, 120, 120), width=2)
    return img


def prescription_rajesh() -> Image.Image:
    return _render(
        [
            ("Dr. Arun Sharma, MBBS, MD (Internal Medicine)", 30),
            ("Reg. No: KA/45678/2015", 22),
            ("City Medical Centre, 12 MG Road, Bengaluru", 22),
            ("--------------------------------------------------------------", 20),
            ("Patient: Rajesh Kumar        Date: 01-Nov-2024", 26),
            ("Age: 39 years   Gender: M", 22),
            ("Chief Complaint: Fever since 3 days, body ache", 22),
            ("--------------------------------------------------------------", 20),
            ("Diagnosis: Viral Fever", 28),
            ("", 10),
            ("Rx:", 24),
            ("1. Tab Paracetamol 650mg  -  1-1-1 x 5 days", 24),
            ("2. Tab Vitamin C 500mg    -  0-0-1 x 7 days", 24),
            ("", 10),
            ("Investigations: CBC, Dengue NS1", 22),
            ("Follow-up: After 5 days if no improvement", 22),
            ("", 16),
            ("[Doctor's Signature]      [Registration Stamp]", 22),
        ]
    )


def hospital_bill_rajesh() -> Image.Image:
    return _render(
        [
            ("CITY MEDICAL CENTRE", 32),
            ("12 MG Road, Bengaluru - 560001", 22),
            ("GSTIN: 29XXXXX1234X1ZX", 20),
            ("--------------------------------------------------------------", 20),
            ("BILL / RECEIPT", 26),
            ("Bill No: CMC/2024/08321     Date: 01-Nov-2024", 22),
            ("Patient Name: Rajesh Kumar", 26),
            ("Age/Gender: 39 / Male", 22),
            ("Referring Doctor: Dr. Arun Sharma", 22),
            ("--------------------------------------------------------------", 20),
            ("DESCRIPTION                 QTY    RATE     AMOUNT", 22),
            ("Consultation Fee (OPD)       1    1000.00   1000.00", 22),
            ("CBC (Complete Blood Count)   1     200.00    200.00", 22),
            ("Dengue NS1 Antigen Test      1     300.00    300.00", 22),
            ("--------------------------------------------------------------", 20),
            ("Subtotal:                                  1500.00", 22),
            ("GST (0% on medical):                          0.00", 22),
            ("Total Amount:                              1500.00", 26),
            ("", 12),
            ("Payment Mode: UPI        Received by: [Cashier Stamp]", 20),
        ]
    )


def pharmacy_bill_clear() -> Image.Image:
    return _render(
        [
            ("HEALTH FIRST PHARMACY", 30),
            ("Drug Lic. No: KA-BLR-4471", 20),
            ("22 Brigade Road, Bengaluru", 22),
            ("--------------------------------------------------------------", 20),
            ("Bill No: HFP-24-09821    Date: 25-Oct-2024", 22),
            ("Patient: Sneha Reddy    Dr: Dr. R. Gupta", 24),
            ("--------------------------------------------------------------", 20),
            ("MEDICINE          QTY    MRP      AMOUNT", 22),
            ("Azithromycin 500    5    24.00    120.00", 22),
            ("Paracetamol 650    10     2.50     25.00", 22),
            ("ORS Sachets         6    18.00    108.00", 22),
            ("--------------------------------------------------------------", 20),
            ("Net Amount:                      253.00", 24),
            ("", 12),
            ("Pharmacist: R. Sharma   [Stamp]", 20),
        ]
    )


def main() -> None:
    OUT.mkdir(exist_ok=True)

    prescription_rajesh().save(OUT / "prescription_rajesh.png")
    hospital_bill_rajesh().save(OUT / "hospital_bill_rajesh.png")

    # A clear pharmacy bill and a deliberately unreadable "phone photo" of it.
    clear = pharmacy_bill_clear()
    clear.save(OUT / "pharmacy_bill_clear.png")
    blurry = clear.filter(ImageFilter.GaussianBlur(radius=7))
    blurry = blurry.point(lambda p: int(90 + p * 0.45))  # wash out contrast
    blurry.save(OUT / "pharmacy_bill_blurry.png")

    print(f"Wrote sample documents to {OUT}/")
    for p in sorted(OUT.glob("*.png")):
        print(f"  - {p.name}")


if __name__ == "__main__":
    main()
