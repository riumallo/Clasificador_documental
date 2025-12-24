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
        r"\banexo de contrato de trabajo\b",
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

    "Prevencion_riesgos": [
        r"\bprevencion de riesgos\b",
        r"\briesgos laborales\b",
        r"\bseguridad\b",
        r"\bhigiene\b",
        r"\bcomite paritario\b",
        r"\bcharla\b",
        r"\binduccion\b",
        r"\bepp\b",
        r"\baccidente\b",
        r"\bprocedimiento\b",
        r"\bseguridad y salud\b",
    ],

}

WEIGHTS = {
    "Anexos": {
        r"\banexo de contrato de trabajo\b": 2.0,
        r"\banexo de contrato\b": 1.5,
    },
    "Cedula_identidad": {
        r"\brut\b": 0.2,
        r"\brun\b": 0.2,
    },
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
        weights = WEIGHTS.get(label, {})
        total_weight = 0.0
        for p in patterns:
            w = float(weights.get(p, 1.0))
            total_weight += w
            if re.search(p, t, flags=re.IGNORECASE):
                matches.append(p)
        score = sum(float(weights.get(p, 1.0)) for p in matches) / max(1.0, total_weight)

        if score > best_score:
            best_score = score
            best_label = label
            best_evidence = matches

    if best_score < threshold:
        return ClassificationResult("Desconocido", best_score, best_evidence)

    return ClassificationResult(best_label, best_score, best_evidence)
