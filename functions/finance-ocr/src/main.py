import os
import re
import httpx
from io import BytesIO
from datetime import date as date_type
from PIL import Image, ImageEnhance
import pytesseract
from transformers import pipeline
from fastapi import UploadFile
from fastapi.responses import JSONResponse
from shared.logger import get_logger

logger = get_logger(__name__)

_FINANCE_URL = os.environ.get("FINANCE_URL", "https://of.giomartins.dev/function/finance")
_CF_CLIENT_ID = os.environ.get("CF_ACCESS_CLIENT_ID", "")
_CF_CLIENT_SECRET = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")

_classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli",
    device=-1,
)

_EXPENSE_CATEGORIES = [
    "Food", "Transport", "Housing", "Health",
    "Entertainment", "Education", "Shopping", "Other",
]
_INCOME_CATEGORIES = [
    "Salary", "Freelance", "Investment", "Gift", "Other"
]

_INCOME_KW = {
    "salário", "salario", "salary", "depósito", "deposito",
    "crédito", "credito", "pix recebido", "transferência recebida",
    "transferencia recebida", "rendimento",
}


def _preprocess(img: Image.Image) -> Image.Image:
    img = img.convert("L")
    return ImageEnhance.Contrast(img).enhance(2.0)


def _ocr(image_bytes: bytes) -> str:
    img = Image.open(BytesIO(image_bytes))
    img = _preprocess(img)
    return pytesseract.image_to_string(img, lang="por+eng", config="--psm 6")


def _extract_amount(text: str) -> float | None:
    # Priority: labeled totals first, then any R$ value, then last numeric value
    patterns = [
        r"(?:TOTAL|VALOR\s+TOTAL|VALOR)[^\d]*R?\$?\s*([\d.,]+)",
        r"R\$\s*([\d.,]+)",
        r"([\d.,]+)\s*(?:\n|$)",
    ]
    amounts = []
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            raw = m.group(1).strip()
            # Brazilian format 1.234,56 → 1234.56
            if re.match(r"^\d{1,3}(?:\.\d{3})+,\d{2}$", raw):
                raw = raw.replace(".", "").replace(",", ".")
            elif "," in raw and raw.rindex(",") == len(raw) - 3:
                raw = raw.replace(".", "").replace(",", ".")
            else:
                raw = raw.replace(",", "")
            try:
                val = float(raw)
                if val > 0:
                    amounts.append(val)
            except ValueError:
                pass
        if amounts:
            return max(amounts)
    return None


def _extract_date(text: str) -> str | None:
    # DD/MM/YYYY
    m = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", text)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    # YYYY-MM-DD
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if m:
        return m.group(0)
    return None


def _classify(text: str) -> tuple[str, str]:
    text_lower = text.lower()
    is_income = any(kw in text_lower for kw in _INCOME_KW)
    categories = _INCOME_CATEGORIES if is_income else _EXPENSE_CATEGORIES
    tx_type = "income" if is_income else "expense"

    result = _classifier(text[:512], candidate_labels=categories, multi_label=False)
    return tx_type, result["labels"][0]


def _description(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 4 and not re.match(r"^[\d\s/.,:-]+$", line):
            return line[:100]
    return "Receipt import"


async def main(file: UploadFile) -> JSONResponse:
    try:
        image_bytes = await file.read()
        logger.info(f"OCR start: filename={file.filename} size={len(image_bytes)}")

        text = _ocr(image_bytes)
        logger.info(f"OCR text: {text[:300]!r}")

        amount = _extract_amount(text)
        if not amount:
            return JSONResponse(
                {"error": "Could not extract amount from receipt"},
                status_code=422,
            )

        tx_date = _extract_date(text) or date_type.today().isoformat()
        tx_type, category = _classify(text)
        description = _description(text)

        transaction = {
            "amount": amount,
            "type": tx_type,
            "category": category,
            "description": description,
            "date": tx_date,
        }
        logger.info(f"Extracted: {transaction}")

        await _record_transaction(transaction)
        return JSONResponse({"status": "ok", "transaction": transaction}, status_code=200)

    except Exception as e:
        logger.error(f"OCR processing failed: {e}", exc_info=True)
        return JSONResponse({"error": "internal server error"}, status_code=500)


async def _record_transaction(data: dict) -> None:
    payload = {
        "amount": str(data["amount"]),
        "type": data["type"],
        "category": data["category"],
        "description": data["description"],
        "date": data.get("date"),
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            _FINANCE_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "CF-Access-Client-Id": _CF_CLIENT_ID,
                "CF-Access-Client-Secret": _CF_CLIENT_SECRET,
            },
            timeout=30.0,
        )
        logger.info(f"Finance response: status={response.status_code}")
        response.raise_for_status()

