import pandas as pd
import streamlit as st
from notion_client import Client

@st.cache_data(ttl=300) 
def fetch_notion_data(notion_token: str, database_id: str) -> pd.DataFrame:
    """Conecta na API do Notion e extrai o banco de dados bruto usando requisição direta."""
    notion = Client(auth=notion_token)
    
    results = []
    
    # REQUISIÇÃO DIRETA: Ignoramos os erros da biblioteca e mandamos a chamada crua
    response = notion.request(
        path=f"databases/{database_id}/query",
        method="POST"
    )
    
    results.extend(response.get("results", []))
    
    # Paginação: Caso você passe de 100 meses no futuro
    while response.get("has_more"):
        response = notion.request(
            path=f"databases/{database_id}/query",
            method="POST",
            body={"start_cursor": response.get("next_cursor")}
        )
        results.extend(response.get("results", []))
        
    rows = []
    for item in results:
        props = item["properties"]
        
        def get_number(prop_name):
            if prop_name in props and props[prop_name].get("number") is not None:
                return float(props[prop_name]["number"])
            return 0.0
            
        def get_select(prop_name):
            if prop_name in props and props[prop_name].get("select") is not None:
                return props[prop_name]["select"]["name"]
            return "Projetado"

        row = {
            "Mês": get_number("Mês"),
            "Status": get_select("Status"),
            "Prestação Construtora": get_number("Prestação Construtora"),
            "Amortização": get_number("Amortização"),
            "EO": get_number("EO"),
            "Aporte Casal": get_number("Aporte Casal")
        }
        rows.append(row)
        
    df = pd.DataFrame(rows).sort_values("Mês").reset_index(drop=True)
    return df

def recalculate_forecast(df: pd.DataFrame, gap_inicial: float, aporte_padrao: float) -> pd.DataFrame:
    """Motor de FP&A: Trava o passado (Fechado) e recalcula o futuro (Projetado)."""
    df = df.copy()
    
    is_fechado = df["Status"] == "Fechado"
    
    # 1. Ajuste do Saldo da Construtora
    pago_construtora = df.loc[is_fechado, "Prestação Construtora"].sum()
    saldo_gap = max(gap_inicial - pago_construtora, 0.0)
    meses_restantes = (~is_fechado).sum()
    
    if meses_restantes > 0:
        parcela_projetada = saldo_gap / meses_restantes
        df.loc[~is_fechado, "Prestação Construtora"] = parcela_projetada

    # 2. Tratamento do Aporte Mensal do Casal
    df.loc[(~is_fechado) & (df["Aporte Casal"] == 0), "Aporte Casal"] = aporte_padrao
    
    # 3. Matemática Financeira Final
    df["Prestação Construtora"] = df["Prestação Construtora"].fillna(0)
    df["EO"] = df["EO"].fillna(0)
    df["Amortização"] = df["Amortização"].fillna(0)
    
    df["Desembolso Real do Mês (R$)"] = df["Prestação Construtora"] + df["EO"] + df["Amortização"]
    df["Poupança Gerada (R$)"] = df["Aporte Casal"] - df["Desembolso Real do Mês (R$)"]
    df["Poupança Acumulada (R$)"] = df["Poupança Gerada (R$)"].cumsum()
    
    df = df.rename(columns={
        "Prestação Construtora": "Parcela Construtora (R$)",
        "EO": "Evolução de Obra (R$)"
    })
    
    return df
