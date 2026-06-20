import math
import pandas as pd
import numpy as np


def annual_to_monthly_rate(annual_rate: float) -> float:
    return (1 + annual_rate) ** (1 / 12) - 1


def generate_sac_schedule(
    principal: float,
    annual_rate: float,
    term_months: int,
) -> pd.DataFrame:
    monthly_rate = annual_to_monthly_rate(annual_rate)
    amortization = principal / term_months
    balance = principal

    rows = []

    for month in range(1, term_months + 1):
        interest = balance * monthly_rate
        payment = amortization + interest
        ending_balance = max(balance - amortization, 0)

        rows.append({
            "Month": month,
            "Opening Balance": balance,
            "Interest": interest,
            "Amortization": amortization,
            "Payment": payment,
            "Ending Balance": ending_balance,
        })

        balance = ending_balance

    return pd.DataFrame(rows)


def generate_price_schedule(
    principal: float,
    annual_rate: float,
    term_months: int,
) -> pd.DataFrame:
    monthly_rate = annual_to_monthly_rate(annual_rate)

    if monthly_rate == 0:
        payment = principal / term_months
    else:
        payment = principal * (
            monthly_rate * (1 + monthly_rate) ** term_months
        ) / ((1 + monthly_rate) ** term_months - 1)

    balance = principal
    rows = []

    for month in range(1, term_months + 1):
        interest = balance * monthly_rate
        amortization = payment - interest
        ending_balance = max(balance - amortization, 0)

        rows.append({
            "Month": month,
            "Opening Balance": balance,
            "Interest": interest,
            "Amortization": amortization,
            "Payment": payment,
            "Ending Balance": ending_balance,
        })

        balance = ending_balance

    return pd.DataFrame(rows)


def generate_amortization_schedule(
    system: str,
    principal: float,
    annual_rate: float,
    term_months: int,
) -> pd.DataFrame:
    if system == "SAC":
        return generate_sac_schedule(principal, annual_rate, term_months)

    if system == "PRICE":
        return generate_price_schedule(principal, annual_rate, term_months)

    raise ValueError(f"Unsupported financing system: {system}")


_SCHEDULE_COLUMNS = ["Month", "Opening Balance", "Interest", "Amortization", "Payment", "Ending Balance"]


def _empty_schedule() -> pd.DataFrame:
    return pd.DataFrame(columns=_SCHEDULE_COLUMNS)


def _sac_reduce_installment(opening_balance, extra_payment, monthly_rate, month, remaining_months) -> pd.DataFrame:
    """SAC — mantém o prazo, recalcula a amortização (parcela cai)."""
    principal = max(opening_balance - extra_payment, 0.0)
    if remaining_months <= 0 or principal <= 0:
        return _empty_schedule()

    amortization = principal / remaining_months
    rows = []
    balance = principal

    for m in range(month, month + remaining_months):
        interest = balance * monthly_rate
        payment = amortization + interest
        ending_balance = max(balance - amortization, 0.0)
        rows.append({
            "Month": m, "Opening Balance": balance, "Interest": interest,
            "Amortization": amortization, "Payment": payment, "Ending Balance": ending_balance,
        })
        balance = ending_balance

    return pd.DataFrame(rows)


def _sac_reduce_term(opening_balance, extra_payment, monthly_rate, month, original_amortization, original_remaining_months) -> pd.DataFrame:
    """SAC — mantém o ritmo de amortização original, encurta o prazo."""
    principal = max(opening_balance - extra_payment, 0.0)
    if principal <= 0 or original_amortization <= 0:
        return _empty_schedule()

    rows = []
    balance = principal
    m = month

    while balance > 0.01 and (m - month) < original_remaining_months:
        amortization = min(original_amortization, balance)
        interest = balance * monthly_rate
        payment = amortization + interest
        ending_balance = max(balance - amortization, 0.0)
        rows.append({
            "Month": m, "Opening Balance": balance, "Interest": interest,
            "Amortization": amortization, "Payment": payment, "Ending Balance": ending_balance,
        })
        balance = ending_balance
        m += 1

    return pd.DataFrame(rows)


def _price_reduce_installment(opening_balance, extra_payment, monthly_rate, month, remaining_months) -> pd.DataFrame:
    """PRICE — mantém o prazo, recalcula a parcela fixa (menor)."""
    principal = max(opening_balance - extra_payment, 0.0)
    if remaining_months <= 0 or principal <= 0:
        return _empty_schedule()

    if monthly_rate == 0:
        payment = principal / remaining_months
    else:
        payment = principal * (
            monthly_rate * (1 + monthly_rate) ** remaining_months
        ) / ((1 + monthly_rate) ** remaining_months - 1)

    rows = []
    balance = principal

    for m in range(month, month + remaining_months):
        interest = balance * monthly_rate
        amortization = payment - interest
        ending_balance = max(balance - amortization, 0.0)
        rows.append({
            "Month": m, "Opening Balance": balance, "Interest": interest,
            "Amortization": amortization, "Payment": payment, "Ending Balance": ending_balance,
        })
        balance = ending_balance

    return pd.DataFrame(rows)


def _price_reduce_term(opening_balance, extra_payment, monthly_rate, month, original_payment, original_remaining_months):
    """PRICE — mantém a parcela fixa original, encurta o prazo."""
    principal = max(opening_balance - extra_payment, 0.0)
    if principal <= 0 or original_payment <= 0:
        return _empty_schedule(), 0

    if monthly_rate <= 0:
        new_remaining_months = int(math.ceil(principal / original_payment))
    elif (principal * monthly_rate) >= original_payment:
        # Parcela não cobre nem os juros do novo saldo — não há redução de prazo possível.
        new_remaining_months = original_remaining_months
    else:
        new_term = -math.log(1 - (principal * monthly_rate) / original_payment) / math.log(1 + monthly_rate)
        new_remaining_months = int(round(new_term))

    new_remaining_months = max(min(new_remaining_months, original_remaining_months), 0)

    rows = []
    balance = principal
    m = month
    count = 0

    while balance > 0.01 and count < new_remaining_months:
        interest = balance * monthly_rate
        amortization = original_payment - interest
        ending_balance = max(balance - amortization, 0.0)
        rows.append({
            "Month": m, "Opening Balance": balance, "Interest": interest,
            "Amortization": amortization, "Payment": original_payment, "Ending Balance": ending_balance,
        })
        balance = ending_balance
        m += 1
        count += 1

    return pd.DataFrame(rows), len(rows)


def simulate_extra_amortization(
    schedule: pd.DataFrame,
    extra_payment: float,
    month: int = 1,
    system: str = "SAC",
    mode: str = "reduce_term",
) -> dict:
    """
    Simula o efeito de um aporte extra no financiamento.

    mode:
      - "reduce_term": mantém a parcela/ritmo, encurta o número de meses.
      - "reduce_installment": mantém o prazo, reduz o valor da parcela.
    """
    system = str(system).upper()
    mode = str(mode).lower()

    if mode not in {"reduce_term", "reduce_installment"}:
        raise ValueError(f"Modo inválido: {mode}. Use 'reduce_term' ou 'reduce_installment'.")
    if system not in {"SAC", "PRICE"}:
        raise ValueError(f"Sistema inválido: {system}. Use 'SAC' ou 'PRICE'.")

    if extra_payment <= 0 or month not in schedule["Month"].values:
        return {
            "new_schedule": schedule.copy(),
            "interest_saved": 0.0,
            "months_reduced": 0,
            "mode": mode,
            "system": system,
            "warning": None,
        }

    original_total_interest = float(schedule["Interest"].sum())
    rows_before = schedule[schedule["Month"] < month]
    opening_balance_at_month = float(schedule.loc[schedule["Month"] == month, "Opening Balance"].iloc[0])
    original_remaining_months = int(schedule["Month"].max() - month + 1)

    first_opening = float(schedule.loc[0, "Opening Balance"])
    monthly_rate = float(schedule.loc[0, "Interest"]) / first_opening if first_opening > 0 else 0.0

    warning = None
    if system == "PRICE" and mode == "reduce_installment":
        warning = (
            "Na Tabela PRICE, reduzir a parcela mantendo o prazo desacelera a amortização do "
            "principal — você paga menos por mês, mas devolve ao banco boa parte do ganho em "
            "juros. Avalie o modo 'reduce_term' para um ganho financeiro maior."
        )

    if extra_payment >= opening_balance_at_month:
        # Quitação total do saldo a partir deste mês.
        new_partial_schedule = _empty_schedule()
        months_reduced = original_remaining_months
        new_total_interest = float(rows_before["Interest"].sum())
    else:
        if system == "SAC" and mode == "reduce_installment":
            new_partial_schedule = _sac_reduce_installment(
                opening_balance_at_month, extra_payment, monthly_rate, month, original_remaining_months
            )
            months_reduced = 0

        elif system == "SAC" and mode == "reduce_term":
            original_amortization = float(schedule.loc[0, "Amortization"])
            new_partial_schedule = _sac_reduce_term(
                opening_balance_at_month, extra_payment, monthly_rate, month,
                original_amortization, original_remaining_months,
            )
            months_reduced = original_remaining_months - len(new_partial_schedule)

        elif system == "PRICE" and mode == "reduce_installment":
            new_partial_schedule = _price_reduce_installment(
                opening_balance_at_month, extra_payment, monthly_rate, month, original_remaining_months
            )
            months_reduced = 0

        else:  # PRICE + reduce_term
            original_payment = float(schedule.loc[0, "Payment"])
            new_partial_schedule, computed_months = _price_reduce_term(
                opening_balance_at_month, extra_payment, monthly_rate, month,
                original_payment, original_remaining_months,
            )
            months_reduced = original_remaining_months - computed_months

        new_total_interest = float(rows_before["Interest"].sum()) + float(new_partial_schedule["Interest"].sum())

    interest_saved = max(original_total_interest - new_total_interest, 0.0)
    new_schedule = pd.concat([rows_before, new_partial_schedule], ignore_index=True)

    return {
        "new_schedule": new_schedule,
        "interest_saved": interest_saved,
        "months_reduced": int(max(months_reduced, 0)),
        "mode": mode,
        "system": system,
        "warning": warning,
    }
