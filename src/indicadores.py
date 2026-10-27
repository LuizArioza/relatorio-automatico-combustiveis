"""
Indicadores do relatório. Tudo calculado a partir das tabelas de leitura.py.
"""
from __future__ import annotations

import pandas as pd

# produtos que entram no relatório (a ANP também publica gasolina aditivada, GNV e diesel S500)
PRODUTOS = ["GASOLINA COMUM", "ETANOL HIDRATADO", "OLEO DIESEL S10", "GLP"]
NOME = {
    "GASOLINA COMUM": "Gasolina comum",
    "ETANOL HIDRATADO": "Etanol",
    "OLEO DIESEL S10": "Diesel S10",
    "GLP": "Gás de cozinha (13 kg)",
}
# regra de bolso: etanol compensa quando custa até 70% do preço da gasolina
LIMITE_PARIDADE = 0.70

UF = {
    "ACRE": "AC", "ALAGOAS": "AL", "AMAPA": "AP", "AMAZONAS": "AM", "BAHIA": "BA", "CEARA": "CE",
    "DISTRITO FEDERAL": "DF", "ESPIRITO SANTO": "ES", "GOIAS": "GO", "MARANHAO": "MA",
    "MATO GROSSO": "MT", "MATO GROSSO DO SUL": "MS", "MINAS GERAIS": "MG", "PARA": "PA",
    "PARAIBA": "PB", "PARANA": "PR", "PERNAMBUCO": "PE", "PIAUI": "PI", "RIO DE JANEIRO": "RJ",
    "RIO GRANDE DO NORTE": "RN", "RIO GRANDE DO SUL": "RS", "RONDONIA": "RO", "RORAIMA": "RR",
    "SANTA CATARINA": "SC", "SAO PAULO": "SP", "SERGIPE": "SE", "TOCANTINS": "TO",
}


def semana_referencia(brasil: pd.DataFrame) -> pd.Timestamp:
    return brasil["data_inicial"].max()


def resumo_nacional(brasil: pd.DataFrame) -> pd.DataFrame:
    """Preço médio Brasil por produto: semana atual, anterior e início da janela."""
    linhas = []
    for prod in PRODUTOS:
        s = brasil[brasil.produto == prod].sort_values("data_inicial")
        if len(s) < 2:
            continue
        atual, anterior, inicio = s.iloc[-1], s.iloc[-2], s.iloc[0]
        linhas.append({
            "produto": NOME[prod],
            "unidade": "R$/13kg" if prod == "GLP" else "R$/l",
            "preco_atual": atual.preco_medio,
            "preco_semana_anterior": anterior.preco_medio,
            "var_semana_rs": atual.preco_medio - anterior.preco_medio,
            "var_semana_pct": 100 * (atual.preco_medio / anterior.preco_medio - 1),
            "semanas_janela": len(s),
            "var_janela_pct": 100 * (atual.preco_medio / inicio.preco_medio - 1),
            "preco_min": atual.preco_min,
            "preco_max": atual.preco_max,
            "postos": int(atual.postos),
        })
    return pd.DataFrame(linhas)


def serie_nacional(brasil: pd.DataFrame) -> pd.DataFrame:
    """Variação % acumulada desde a primeira semana da janela (deixa produtos de unidades diferentes comparáveis)."""
    s = brasil[brasil.produto.isin(PRODUTOS)].pivot(index="data_inicial", columns="produto", values="preco_medio")
    s = s[[p for p in PRODUTOS if p in s.columns]]
    return (100 * (s / s.iloc[0] - 1)).rename(columns=NOME)


def precos_estados(estados: pd.DataFrame, produto: str) -> pd.DataFrame:
    """Preço médio por UF na semana mais recente + variação contra a semana anterior."""
    e = estados[estados.produto == produto]
    if e.empty:
        return pd.DataFrame()
    datas = sorted(e.data_inicial.unique())
    atual = e[e.data_inicial == datas[-1]].set_index("estado")
    df = pd.DataFrame({
        "uf": atual.index.map(UF),
        "regiao": atual.regiao,
        "preco_medio": atual.preco_medio,
        "postos": atual.postos.astype(int),
    })
    if len(datas) > 1:
        ant = e[e.data_inicial == datas[-2]].set_index("estado").preco_medio
        df["var_semana_rs"] = df.preco_medio - ant.reindex(df.index)
        df["var_semana_pct"] = 100 * (df.preco_medio / ant.reindex(df.index) - 1)
    return df.sort_values("preco_medio").reset_index()


def paridade_etanol(estados: pd.DataFrame) -> pd.DataFrame:
    """Razão etanol/gasolina por UF na semana mais recente."""
    data = estados.data_inicial.max()
    e = estados[estados.data_inicial == data].pivot(index="estado", columns="produto", values="preco_medio")
    if not {"ETANOL HIDRATADO", "GASOLINA COMUM"} <= set(e.columns):
        return pd.DataFrame()
    e = e[["ETANOL HIDRATADO", "GASOLINA COMUM"]].dropna()
    df = pd.DataFrame({
        "uf": e.index.map(UF),
        "etanol": e["ETANOL HIDRATADO"],
        "gasolina": e["GASOLINA COMUM"],
    })
    df["paridade"] = df.etanol / df.gasolina
    df["compensa_etanol"] = df.paridade <= LIMITE_PARIDADE
    return df.sort_values("paridade").reset_index()


def destaques(brasil: pd.DataFrame, estados: pd.DataFrame) -> dict:
    """Números que alimentam o resumo em texto (e o prompt da IA, quando ligada)."""
    nac = resumo_nacional(brasil)
    out = {
        "semana": semana_referencia(brasil),
        "nacional": nac.to_dict("records"),
    }
    gas = precos_estados(estados, "GASOLINA COMUM")
    if not gas.empty:
        out["gasolina_mais_barata"] = gas.iloc[0][["uf", "preco_medio"]].to_dict()
        out["gasolina_mais_cara"] = gas.iloc[-1][["uf", "preco_medio"]].to_dict()
        if "var_semana_pct" in gas:
            g = gas.dropna(subset=["var_semana_pct"]).sort_values("var_semana_pct")
            out["gasolina_maior_alta"] = g.iloc[-1][["uf", "var_semana_pct"]].to_dict()
            out["gasolina_maior_queda"] = g.iloc[0][["uf", "var_semana_pct"]].to_dict()
    par = paridade_etanol(estados)
    if not par.empty:
        out["ufs_etanol_compensa"] = par.loc[par.compensa_etanol, "uf"].tolist()
        out["melhor_paridade"] = par.iloc[0][["uf", "paridade"]].to_dict()
    return out
