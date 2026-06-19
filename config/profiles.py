from core.models import BuyerProfile


VINICIUS_JU = BuyerProfile(
    name="Vinicius & Ju",
    property_value=705_900,
    down_payment=55_000,
    financing_ceiling=636_300,
    monthly_builder_installment=41.41,
    months_until_keys=30,
    household_income=14_868,
    financing_system="SAC",
    term_months=308,
    annual_interest_rate=0.1119,
    approved_first_installment=8_225.12,
    approved_last_installment=2_109.25,
    initial_construction_evolution=1_480.52,
    apartment_size_m2=58.49,
    condo_brl_per_m2=10,
    itbi_registry_paid_by_builder=True,
)


JOAO_MARI = BuyerProfile(
    name="João & Mari",
    property_value=437_000,
    down_payment=65_000,
    financing_ceiling=298_622,
    monthly_builder_installment=0,
    months_until_keys=39,
    household_income=6_200,
    financing_system="PRICE",
    term_months=420,
    annual_interest_rate=0.0793,
    approved_first_installment=2_153.22,
    approved_last_installment=None,
    initial_construction_evolution=100,
    apartment_size_m2=45,
    condo_brl_per_m2=10,
    itbi_registry_paid_by_builder=False,
)


PROFILES = {
    "Vinicius & Ju": VINICIUS_JU,
    "João & Mari": JOAO_MARI,
}