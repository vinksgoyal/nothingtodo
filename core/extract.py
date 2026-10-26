import io
import logging
import subprocess
from pathlib import Path

import pytesseract
from PIL import Image


def _ocr_image(img: Image.Image) -> tuple[str, float]:
    grayscale = img.convert("L")
    data = pytesseract.image_to_data(
        grayscale,
        output_type=pytesseract.Output.DICT,
    )
    words: list[str] = []
    confidences: list[float] = []
    for word, confidence in zip(data["text"], data["conf"]):
        if confidence == "-1":
            continue
        words.append(word)
        confidences.append(float(confidence))

    average_confidence = (
        sum(confidences) / len(confidences) / 100 if confidences else 0.0
    )
    return " ".join(words), average_confidence


def extract_text(path: Path) -> tuple[str, float]:
    try:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return path.read_text(), 1.0

        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            with Image.open(path) as img:
                return _ocr_image(img)

        if suffix == ".pdf":
            text_result = subprocess.run(
                ["pdftotext", "-l", "3", str(path), "-"],
                capture_output=True,
                text=True,
                check=True,
            )
            text = text_result.stdout[:2000]
            if len(text) >= 40:
                return text, 1.0

            image_result = subprocess.run(
                ["pdftoppm", "-png", "-r", "150", "-f", "1", "-l", "1", str(path), "-"],
                capture_output=True,
                check=True,
            )
            with Image.open(io.BytesIO(image_result.stdout)) as img:
                return _ocr_image(img)

        return "", 0.0
    except Exception as exc:
        logging.debug("Text extraction failed: %s", type(exc).__name__)
        return "", 0.0


def ocr_confidence_ok(conf: float) -> bool:
    return conf >= 0.55
