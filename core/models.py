from dataclasses import dataclass
from typing import Literal


FinancingSystem = Literal["SAC", "PRICE"]
ConstructionCurve = Literal["Linear", "S-Curve", "Back-loaded"]
RenovationPackage = Literal["Basic", "Recommended", "Premium"]


@dataclass(frozen=True)
class BuyerProfile:
    name: str
    property_value: float
    down_payment: float
    financing_ceiling: float
    monthly_builder_installment: float
    months_until_keys: int
    household_income: float
    financing_system: FinancingSystem
    term_months: int
    annual_interest_rate: float
    approved_first_installment: float
    approved_last_installment: float | None
    initial_construction_evolution: float
    apartment_size_m2: float | None = None
    condo_brl_per_m2: float | None = None
    itbi_registry_paid_by_builder: bool = False


@dataclass(frozen=True)
class InvestmentAsset:
    name: str
    annual_return: float
    annual_volatility: float
    tax_rate: float
    liquidity_score: float
    risk_score: float


@dataclass(frozen=True)
class RenovationCategory:
    name: str
    base_cost_per_m2: float
    weight: float