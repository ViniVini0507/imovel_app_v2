import streamlit as st


def money(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def status_badge(status: str) -> str:
    return {
        "green": "🟢 Verde",
        "yellow": "🟡 Amarelo",
        "red": "🔴 Vermelho",
    }.get(status, status)


def section(title: str, description: str | None = None):
    st.subheader(title)

    if description:
        st.caption(description)