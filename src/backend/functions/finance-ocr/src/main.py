import httpx
from io import BytesIO
from PIL import Image, ImageEnhance
import pytesseract
from fastapi import UploadFile
from fastapi.responses import JSONResponse
from shared.logger import get_logger
from shared.secret_manager import SecretManager
from shared.timezone_handler import TimezoneAware
from src.parser import classify, description, extract_amount, extract_date

_SP = TimezoneAware("America/Sao_Paulo")
logger = get_logger(__name__)

_FINANCE_URL = "https://of.giomartins.dev/function/finance"
_CF_CLIENT_ID = None
_CF_CLIENT_SECRET = None


def _init():
    global _CF_CLIENT_ID, _CF_CLIENT_SECRET
    if _CF_CLIENT_ID is not None:
        return
    sm = SecretManager()
    _CF_CLIENT_ID = sm.get_secret("CF_ACCESS_CLIENT_ID")
    _CF_CLIENT_SECRET = sm.get_secret("CF_ACCESS_CLIENT_SECRET")


def _preprocess(img: Image.Image) -> Image.Image:
    img = img.convert("L")
    return ImageEnhance.Contrast(img).enhance(2.0)


def _ocr(image_bytes: bytes) -> str:
    img = Image.open(BytesIO(image_bytes))
    img = _preprocess(img)
    return pytesseract.image_to_string(img, lang="por+eng", config="--psm 6")


async def main(file: UploadFile) -> JSONResponse:
    _init()
    try:
        image_bytes = await file.read()
        logger.info(f"OCR start: filename={file.filename} size={len(image_bytes)}")

        text = _ocr(image_bytes)
        logger.info(f"OCR text: {text[:300]!r}")

        amount = extract_amount(text)
        if not amount:
            return JSONResponse(
                {"error": "Could not extract amount from receipt"},
                status_code=422,
            )

        tx_date = extract_date(text) or _SP.now.date().isoformat()
        tx_type, category = classify(text)
        desc = description(text)

        transaction = {
            "amount": amount,
            "type": tx_type,
            "category": category,
            "description": desc,
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
