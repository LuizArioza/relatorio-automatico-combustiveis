"""
Gera o relatório semanal de preços de combustíveis.

Uso:
    python main.py              # baixa as últimas 12 semanas da ANP e gera o relatório
    python main.py --semanas 8  # janela menor
    python main.py --offline    # usa a amostra em tests/fixtures (sem internet)

Saída em reports/<data da semana>/ e uma cópia em reports/ultimo/.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

import graficos  # noqa: E402
import indicadores as ind  # noqa: E402
import relatorio  # noqa: E402
from coleta import baixar_semanas  # noqa: E402
from leitura import ler_semanas  # noqa: E402
from resumo import gerar_resumo  # noqa: E402


def tabela_nacional_excel(nac):
    return nac.rename(columns={
        "produto": "Produto", "unidade": "Unidade", "preco_atual": "Preço atual",
        "preco_semana_anterior": "Semana anterior", "var_semana_rs": "Var. semana (R$)",
        "var_semana_pct": "Var. semana (%)", "var_janela_pct": "Var. janela (%)",
        "semanas_janela": "Semanas na janela", "preco_min": "Mínimo", "preco_max": "Máximo",
        "postos": "Postos pesquisados",
    })


def main(argv=None) -> Path:
    p = argparse.ArgumentParser()
    p.add_argument("--semanas", type=int, default=12)
    p.add_argument("--offline", action="store_true")
    p.add_argument("--saida", type=Path, default=RAIZ / "reports")
    args = p.parse_args(argv)

    inicio = time.perf_counter()
    print("1/5 Coletando dados...")
    if args.offline:
        sys.path.insert(0, str(RAIZ / "tests" / "fixtures"))
        from gerar_xlsx import gerar
        arquivos = gerar(Path(tempfile.mkdtemp()))[: args.semanas]
    else:
        arquivos = baixar_semanas(RAIZ / "data" / "raw", args.semanas)

    print("2/5 Lendo planilhas...")
    brasil, estados = ler_semanas(arquivos)
    semana = ind.semana_referencia(brasil)

    print("3/5 Calculando indicadores...")
    nacional = ind.resumo_nacional(brasil)
    gasolina = ind.precos_estados(estados, "GASOLINA COMUM")
    paridade = ind.paridade_etanol(estados)
    destaques = ind.destaques(brasil, estados)
    texto, origem = gerar_resumo(destaques)

    print("4/5 Gráficos...")
    pasta = args.saida / semana.strftime("%Y-%m-%d")
    pasta.mkdir(parents=True, exist_ok=True)
    media_gas = nacional.loc[nacional.produto == "Gasolina comum", "preco_atual"].iloc[0]
    figuras = {
        "tendencia": graficos.tendencia_nacional(ind.serie_nacional(brasil), pasta),
        "gasolina": graficos.gasolina_por_estado(gasolina, media_gas, pasta),
        "paridade": graficos.paridade_etanol(paridade, pasta),
    }

    print("5/5 Relatórios...")
    historico = (brasil[brasil.produto.isin(ind.PRODUTOS)]
                 .assign(produto=lambda d: d.produto.map(ind.NOME))
                 [["data_inicial", "produto", "preco_medio", "preco_min", "preco_max", "postos"]]
                 .rename(columns={"data_inicial": "Semana", "produto": "Produto", "preco_medio": "Preço médio",
                                  "preco_min": "Mínimo", "preco_max": "Máximo", "postos": "Postos pesquisados"}))
    estados_tab = (estados[estados.data_inicial == estados.data_inicial.max()]
                   .assign(UF=lambda d: d.estado.map(ind.UF))
                   [["UF", "regiao", "produto", "preco_medio", "preco_min", "preco_max", "postos"]]
                   .rename(columns={"regiao": "Região", "produto": "Produto", "preco_medio": "Preço médio",
                                    "preco_min": "Mínimo", "preco_max": "Máximo", "postos": "Postos pesquisados"}))
    relatorio.gerar_excel(pasta / "relatorio.xlsx", {
        "Resumo": tabela_nacional_excel(nacional),
        "Histórico Brasil": historico,
        "Estados (semana)": estados_tab,
        "Paridade etanol": paridade[["uf", "etanol", "gasolina", "paridade", "compensa_etanol"]].rename(columns={
            "uf": "UF", "etanol": "Etanol", "gasolina": "Gasolina", "paridade": "Paridade",
            "compensa_etanol": "Etanol compensa?"}),
    })
    relatorio.gerar_pdf(pasta / "relatorio.pdf", semana, texto, origem, nacional, figuras)
    relatorio.gerar_markdown(pasta / "RESUMO.md", semana, texto, origem, nacional)

    ultimo = args.saida / "ultimo"
    shutil.rmtree(ultimo, ignore_errors=True)
    shutil.copytree(pasta, ultimo)

    print(f"\nPronto em {time.perf_counter() - inicio:.1f}s -> {pasta.relative_to(RAIZ) if pasta.is_relative_to(RAIZ) else pasta}")
    print(f"Resumo ({origem}): {texto}")
    return pasta


if __name__ == "__main__":
    main()
