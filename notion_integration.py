import pandas as pd
import streamlit as st
from notion_client import Client

@st.cache_data(ttl=300) 
def fetch_notion_data(notion_token: str, database_id: str) -> pd.DataFrame:
    """Conecta na API do Notion forçando a versão estável e extrai o banco de dados."""
    
    # 1. Blindagem: .strip() remove qualquer quebra de linha ou espaço invisível
    token_clean = notion_token.strip()
    db_id_clean = database_id.strip()
    
    # 2. Forçamos a versão 2022-06-28 para acessar a URL clássica sem o erro de data_sources
    notion = Client(auth=token_clean, notion_version="2022-06-28")
    
    results = []
    
    # 3. Requisição direta na URL clássica
    response = notion.request(
        path=f"databases/{db_id_clean}/query",
        method="POST"
    )
    
    results.extend(response.get("results", []))
    
    # Paginação para quando você tiver dezenas de meses
    while response.get("has_more"):
        response = notion.request(
            path=f"databases/{db_id_clean}/query",
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
    """Motor de FP&A: Respeita os dados do Notion e calcula os totais de caixa."""
    df = df.copy()
    
    is_fechado = df["Status"] == "Fechado"
    
    # 1. Tratamento do Aporte Mensal do Casal (Se estiver vazio no Notion, assume os 6000)
    df.loc[(~is_fechado) & (df["Aporte Casal"] == 0), "Aporte Casal"] = aporte_padrao
    
    # 2. Limpeza de dados vazios (Mantendo os valores exatos da Construtora que você digitou)
    df["Prestação Construtora"] = df["Prestação Construtora"].fillna(0)
    df["EO"] = df["EO"].fillna(0)
    df["Amortização"] = df["Amortização"].fillna(0)
    
    # 3. Matemática de Fluxo de Caixa Final
    df["Desembolso Real do Mês (R$)"] = df["Prestação Construtora"] + df["EO"] + df["Amortização"]
    df["Poupança Gerada (R$)"] = df["Aporte Casal"] - df["Desembolso Real do Mês (R$)"]
    df["Poupança Acumulada (R$)"] = df["Poupança Gerada (R$)"].cumsum()
    
    df = df.rename(columns={
        "Prestação Construtora": "Parcela Construtora (R$)",
        "EO": "Evolução de Obra (R$)"
    })
    
    return df
