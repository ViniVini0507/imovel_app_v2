from core.models import InvestmentAsset

DEFAULT_CDI = 0.105
DEFAULT_SELIC = 0.105
DEFAULT_INFLATION = 0.045

ASSETS = {
    "Liquidity": InvestmentAsset(
        name="Liquidity - CDB / Tesouro Selic",
        annual_return=0.102,
        annual_volatility=0.005,
        tax_rate=0.175,
        liquidity_score=1.0,
        risk_score=0.05,
    ),
    "PostFixed": InvestmentAsset(
        name="Post-fixed - CDB 105% CDI",
        annual_return=DEFAULT_CDI * 1.05,
        annual_volatility=0.012,
        tax_rate=0.175,
        liquidity_score=0.75,
        risk_score=0.12,
    ),
    "TaxFree": InvestmentAsset(
        name="Tax-free - LCI/LCA",
        annual_return=0.092,
        annual_volatility=0.008,
        tax_rate=0.0,
        liquidity_score=0.65,
        risk_score=0.10,
    ),
    "ControlledRisk": InvestmentAsset(
        name="Controlled Risk - Multimarket",
        annual_return=0.125,
        annual_volatility=0.055,
        tax_rate=0.15,
        liquidity_score=0.45,
        risk_score=0.35,
    ),
}

RENOVATION_PACKAGES = {
    "Basic": {
        "civil_work": 650,
        "cabinetry": 900,
        "appliances": 450,
        "lighting": 180,
        "ac": 280,
        "decor": 220,
    },
    "Recommended": {
        "civil_work": 950,      # mantém — já validado
        "cabinetry": 0,         # remover do cálculo por m²
        "appliances": 0,        # remover do cálculo por m²
        "lighting": 280,        # leve ajuste para baixo
        "ac": 0,                # já tratado por unidade, não por m²
        "decor": 380,           # mantém
    },
    "Premium": {
        "civil_work": 1450,
        "cabinetry": 2200,
        "appliances": 1200,
        "lighting": 520,
        "ac": 750,
        "decor": 650,
    },
}