import re

_KEYWORDS: dict[str, list[str]] = {
    "Transaction": [
        "pix", "ted", "doc", "transferência", "transferencia", "débito",
        "debito", "boleto", "pagamento", "uber", "99app", "taxi",
        "posto ", "shell", "petrobras", "ipiranga", "combustível",
        "gasolina", "estacionamento", "pedágio", "metrô", "ônibus",
        "passagem", "gol ", "latam", "azul ", "aluguel", "condomínio",
        "copasa", "cemig", "sabesp", "enel", "neoenergia", "vivo",
        "claro", "tim ", "oi ", "net ", "internet", "conta de luz",
    ],
    "Food": [
        "restaurante", "lanchonete", "pizzaria", "padaria", "supermercado",
        "mercado", "hortifruti", "açougue", "peixaria", "ifood", "rappi",
        "uber eats", "mcdonald", "burger", "subway", "pizza", "sushi",
        "hamburguer", "lanche", "café", "coffee", "pão de açúcar",
        "carrefour", "extra ", "wal-mart", "atacadão", "assaí", "makro",
        "panificadora", "sorveteria", "doceria", "bistrô",
    ],
    "Health": [
        "farmácia", "drogaria", "ultrafarma", "droga", "pague menos",
        "raia", "dpsp", "panvel", "hospital", "clínica", "médico",
        "dentista", "laboratório", "exame", "consulta", "plano de saúde",
        "unimed", "bradesco saúde", "amil", "sulamerica", "hapvida",
        "notredame", "remédio", "medicamento",
    ],
    "Entertainment": [
        "netflix", "spotify", "amazon prime", "disney+", "hbo", "globoplay",
        "paramount", "apple tv", "cinema", "ingresso", "teatro", "show",
        "evento", "live", "steam", "playstation", "xbox", "nintendo",
        "game", "parque", "museu",
    ],
    "Education": [
        "escola", "faculdade", "universidade", "curso", "udemy", "coursera",
        "alura", "livro", "livraria", "kindle", "material escolar",
        "mensalidade", "matrícula", "apostila", "treinamento",
    ],
    "Shopping": [
        "americanas", "magazine luiza", "magalu", "submarino", "amazon",
        "mercado livre", "shopee", "shein", "zara", "renner", "c&a",
        "riachuelo", "hering", "nike", "adidas", "centauro", "decathlon",
        "leroy merlin", "tok stok", "casas bahia", "ponto frio",
        "fast shop", "kabum", "terabyte",
    ],
}

_INCOME_KW = {
    "salário", "salario", "depósito", "deposito", "crédito em conta",
    "credito em conta", "pix recebido", "transferência recebida",
    "transferencia recebida", "rendimento", "dividendo", "freelance",
    "pagamento recebido",
}


def classify(text: str) -> tuple[str, str]:
    text_lower = text.lower()
    if any(kw in text_lower for kw in _INCOME_KW):
        return "income", "Transaction"
    scores: dict[str, int] = {cat: 0 for cat in _KEYWORDS}
    for cat, keywords in _KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[cat] += 1
    best = max(scores, key=lambda c: scores[c])
    return "expense", best if scores[best] > 0 else "Other"


def extract_amount(text: str) -> float | None:
    patterns = [
        r"(?:TOTAL|VALOR\s+TOTAL|VALOR)[^\d]*R?\$?\s*([\d.,]+)",
        r"R\$\s*([\d.,]+)",
        r"([\d.,]+)\s*(?:\n|$)",
    ]
    for pattern in patterns:
        amounts = []
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            raw = m.group(1).strip()
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


def extract_date(text: str) -> str | None:
    m = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", text)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if m:
        return m.group(0)
    return None


def description(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if len(line) > 4 and not re.match(r"^[\d\s/.,:-]+$", line):
            return line[:100]
    return "Receipt import"
