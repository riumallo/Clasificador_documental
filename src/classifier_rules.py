import re
from dataclasses import dataclass

@dataclass
class ClassificationResult:
    label: str
    score: float
    evidence: list[str]

KEYWORDS = {
    "Contratos": [
        r"\bcontrato de trabajo\b",
        r"\bCONTRATO\b",
        r"\bempleador\b",
        r"\btrabajador\b",
        r"\bjornada\b",
        r"\bremuneraci[oó]n\b",
        r"\bcl[aá]usula\b",
    ],
    "Anexos": [
        r"\banexo\b",
        r"\banexo de contrato\b",
        r"\bmodificaci[oó]n\b",
        r"\bse deja constancia\b",
    ],
    "Certificados": [
        r"\bcertificado\b",
        r"\bcertifico\b",
        r"\bse certifica\b",
        r"\bconstancia\b",
        r"\bcertificado antecedentes\b",
        r"\bcertificado de antecedentes\b",
        r"\bComprobante de Seguro Obligatorio\b",
    ],
    "Cartas": [
        r"\bseñor\(a\)\b",
        r"\bpresente\b",
        r"\bde mi consideraci[oó]n\b",
        r"\batentamente\b",
    ],
    "Finiquitos": [
        r"\bfiniquito\b",
        r"\bindemnizaci[oó]n\b",
        r"\bt[eé]rmino de contrato\b",
        r"\bratifican\b",
        r"\binspecci[oó]n del trabajo\b",
    ],
    "Cedula_identidad": [
        r"\bcedula de identidad\b",
        r"\bcedula identidad\b",
        r"\bcarnet de identidad\b",
        r"\brut\b",
        r"\brun\b",
        r"\bregistro civil\b",
    ],
    "comprobantes": [
        r"\bcomprobante\b",
        r"\bseguro\b",
        r"\bboleta\b",
        r"\bfactura\b",
        r"\brecibo\b",
        r"\btotal a pagar\b",
        r"\bsubtotal\b",
        r"\biva\b",
    ],

    "Liquidaciones": [
        r"\bliquidaciones\b",
        r"\bliquidacion\b",
        r"\bliquidacion de sueldo\b",
    ],

}

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text

def classify_text_rules(text: str, threshold: float = 0.12) -> ClassificationResult:
    """
    score = matches / total_keywords (por categoría). Simple y efectivo para partir.
    threshold: mínimo para no quedar en Desconocido
    """
    t = normalize(text)
    best_label = "Desconocido"
    best_score = 0.0
    best_evidence = []

    for label, patterns in KEYWORDS.items():
        matches = []
        for p in patterns:
            if re.search(p, t, flags=re.IGNORECASE):
                matches.append(p)
        score = len(matches) / max(1, len(patterns))

        if score > best_score:
            best_score = score
            best_label = label
            best_evidence = matches

    if best_score < threshold:
        return ClassificationResult("Desconocido", best_score, best_evidence)

    return ClassificationResult(best_label, best_score, best_evidence)
