"""
Lê os .xlsx da ANP e devolve tabelas "limpas" (uma linha por semana/local/produto).

Layout do arquivo (conferido nos resumos de 2026):
  - abas CAPITAIS, MUNICIPIOS, ESTADOS, REGIOES, BRASIL
  - umas 9 linhas de título e o cabeçalho por volta da linha 10
  - datas como data do Excel

Para não depender da linha exata do cabeçalho, procuro a linha que começa com
"DATA INICIAL". Se a ANP mudar o título de lugar, continua funcionando.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUNAS = {
    "DATA INICIAL": "data_inicial",
    "DATA FINAL": "data_final",
    "REGIAO": "regiao",
    "ESTADOS": "estado",
    "PRODUTO": "produto",
    "NÚMERO DE POSTOS PESQUISADOS": "postos",
    "UNIDADE DE MEDIDA": "unidade",
    "PREÇO MÉDIO REVENDA": "preco_medio",
    "PREÇO MÍNIMO REVENDA": "preco_min",
    "PREÇO MÁXIMO REVENDA": "preco_max",
}


def _para_data(s: pd.Series) -> pd.Series:
    # pode vir como datetime ou como número serial do Excel, depende do arquivo
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_datetime(s, unit="D", origin="1899-12-30")
    return pd.to_datetime(s)


def ler_aba(arquivo: Path, aba: str) -> pd.DataFrame:
    bruto = pd.read_excel(arquivo, sheet_name=aba, header=None)
    linha_cab = bruto.index[bruto.iloc[:, 0].astype(str).str.strip().str.upper() == "DATA INICIAL"]
    if len(linha_cab) == 0:
        raise ValueError(f"{arquivo.name}/{aba}: cabeçalho 'DATA INICIAL' não encontrado")

    df = bruto.iloc[linha_cab[0] + 1:].copy()
    df.columns = [str(c).strip().upper() for c in bruto.iloc[linha_cab[0]]]
    df = df.rename(columns=COLUNAS)
    df = df[[c for c in COLUNAS.values() if c in df.columns]]
    df = df.dropna(subset=["data_inicial", "produto"])

    df["data_inicial"] = _para_data(df["data_inicial"])
    df["data_final"] = _para_data(df["data_final"])
    for c in ["postos", "preco_medio", "preco_min", "preco_max"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["produto"] = df["produto"].str.strip().str.upper()
    return df.reset_index(drop=True)


def ler_semanas(arquivos: list[Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Junta várias semanas. Retorna (brasil, estados)."""
    brasil, estados = [], []
    for arq in arquivos:
        brasil.append(ler_aba(arq, "BRASIL"))
        estados.append(ler_aba(arq, "ESTADOS"))

    br = (pd.concat(brasil).drop_duplicates(["data_inicial", "produto"])
            .sort_values(["produto", "data_inicial"]).reset_index(drop=True))
    est = pd.concat(estados)
    if not est.empty:
        est = (est.drop_duplicates(["data_inicial", "estado", "produto"])
                  .sort_values(["produto", "estado", "data_inicial"]).reset_index(drop=True))
    return br, est
