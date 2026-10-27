"""
Recria arquivos no mesmo layout do resumo semanal da ANP a partir das amostras em CSV
(12 semanas reais de out/2026, extraídas dos arquivos oficiais).

Serve para os testes e para rodar o pipeline offline (`python main.py --offline`).
Nos dados de amostra, a aba ESTADOS só vem preenchida nas 2 semanas mais recentes.
"""
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

AQUI = Path(__file__).parent
ORIGEM_EXCEL = datetime(1899, 12, 30)

CAB_ESTADOS = ["DATA INICIAL", "DATA FINAL", "REGIAO", "ESTADOS", "PRODUTO",
               "NÚMERO DE POSTOS PESQUISADOS", "UNIDADE DE MEDIDA", "PREÇO MÉDIO REVENDA",
               "DESVIO PADRÃO REVENDA", "PREÇO MÍNIMO REVENDA", "PREÇO MÁXIMO REVENDA",
               "COEF DE VARIAÇÃO REVENDA"]
CAB_BRASIL = ["DATA INICIAL", "DATA FINAL", "BRASIL", "PRODUTO", "NÚMERO DE POSTOS PESQUISADOS",
              "UNIDADE DE MEDIDA", "PREÇO MÉDIO REVENDA", "DESVIO PADRÃO REVENDA",
              "PREÇO MÍNIMO REVENDA", "PREÇO MÁXIMO REVENDA", "COEF DE VARIAÇÃO REVENDA"]
UNIDADE = {"GLP": "R$/13kg", "GNV": "R$/m³"}


def _titulo(ws, tipo):
    ws["A1"] = "AGÊNCIA NACIONAL DO PETRÓLEO, GÁS NATURAL E BIOCOMBUSTÍVEIS - ANP"
    ws["A3"] = "LEVANTAMENTO DE PREÇOS DE COMBUSTÍVEIS"
    ws["A6"] = "INTERVALO DE TEMPO: SEMANAL"
    ws["A8"] = f"TIPO RELATÓRIO: {tipo}"


def gerar(destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    br = pd.read_csv(AQUI / "amostra_brasil.csv", sep=";")
    est = pd.read_csv(AQUI / "amostra_estados.csv", sep=";")

    arquivos = []
    for serial in sorted(br["data_serial"].unique(), reverse=True):
        ini = ORIGEM_EXCEL + timedelta(days=int(serial))
        fim = ini + timedelta(days=6)
        wb = Workbook()
        wb.remove(wb.active)
        for aba in ["CAPITAIS", "MUNICIPIOS", "ESTADOS", "REGIOES", "BRASIL"]:
            ws = wb.create_sheet(aba)
            _titulo(ws, aba)

        ws = wb["ESTADOS"]
        ws.append([])
        ws.append(CAB_ESTADOS)  # linha 10
        for r in est[est.data_serial == serial].itertuples():
            ws.append([ini, fim, r.regiao, r.estado, r.produto, r.postos,
                       UNIDADE.get(r.produto, "R$/l"), r.preco_medio, None, r.preco_min, r.preco_max, None])

        ws = wb["BRASIL"]
        ws.append([])
        ws.append(CAB_BRASIL)
        for r in br[br.data_serial == serial].itertuples():
            ws.append([ini, fim, "BRASIL", r.produto, r.postos, UNIDADE.get(r.produto, "R$/l"),
                       r.preco_medio, None, r.preco_min, r.preco_max, None])

        arq = destino / f"resumo_semanal_lpc_{ini:%Y_%m_%d}-{fim:%Y_%m_%d}.xlsx"
        wb.save(arq)
        arquivos.append(arq)
    return arquivos


if __name__ == "__main__":
    for a in gerar(Path("data/raw_amostra")):
        print(a)
