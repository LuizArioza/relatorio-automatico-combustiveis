"""
Gráficos do relatório (PNG). Mesma paleta nos três: azul = destaque, cinza = contexto.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import pandas as pd  # noqa: E402

from indicadores import LIMITE_PARIDADE  # noqa: E402

AZUL, CINZA, VERMELHO, VERDE, LARANJA = "#1F6FB2", "#A3ACB6", "#C8463D", "#2E8B57", "#E08A2E"
CORES = {"Gasolina comum": AZUL, "Etanol": VERDE, "Diesel S10": VERMELHO, "Gás de cozinha (13 kg)": LARANJA}

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight", "font.size": 10,
    "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "axes.axisbelow": True,
})


def _fmt_data(d: pd.Timestamp) -> str:
    meses = "jan fev mar abr mai jun jul ago set out nov dez".split()
    return f"{d.day:02d}/{meses[d.month - 1]}"


def tendencia_nacional(serie: pd.DataFrame, destino: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for col in serie.columns:
        ax.plot(serie.index, serie[col], marker="o", ms=3, lw=2, color=CORES.get(col, CINZA), label=col)
        ax.annotate(f"{serie[col].iloc[-1]:+.1f}%".replace(".", ","), (serie.index[-1], serie[col].iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=9,
                    color=CORES.get(col, CINZA), fontweight="bold")
    ax.axhline(0, color="#555", lw=0.8)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_xticks(serie.index)
    ax.set_xticklabels([_fmt_data(d) for d in serie.index], rotation=45, ha="right", fontsize=8)
    ax.set_title(f"Variação acumulada do preço médio Brasil nas últimas {len(serie)} semanas")
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=8.5)
    arq = destino / "tendencia_nacional.png"
    fig.savefig(arq)
    plt.close(fig)
    return arq


def gasolina_por_estado(df: pd.DataFrame, media_brasil: float, destino: Path) -> Path:
    d = df.sort_values("preco_medio")
    fig, ax = plt.subplots(figsize=(8, 7))
    cores = [AZUL if i == 0 else (VERMELHO if i == len(d) - 1 else CINZA) for i in range(len(d))]
    ax.barh(d.uf, d.preco_medio, color=cores)
    for y, (v, var) in enumerate(zip(d.preco_medio, d.get("var_semana_pct", [None] * len(d)))):
        txt = f"R$ {v:.2f}".replace(".", ",")
        if var is not None and pd.notna(var):
            txt += f"  ({var:+.1f}%)".replace(".", ",")
        ax.text(v + 0.02, y, txt, va="center", fontsize=7.5)
    ax.axvline(media_brasil, ls="--", color="#333", lw=0.9)
    ax.text(media_brasil, len(d) - 0.2, f" média Brasil R$ {media_brasil:.2f}".replace(".", ","),
            fontsize=8, va="bottom")
    ax.set_xlim(d.preco_medio.min() * 0.92, d.preco_medio.max() * 1.07)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"R$ {v:.2f}".replace(".", ",")))
    ax.set_title("Gasolina comum: preço médio por estado (R$/l) e variação na semana")
    ax.grid(axis="y", visible=False)
    arq = destino / "gasolina_por_estado.png"
    fig.savefig(arq)
    plt.close(fig)
    return arq


def paridade_etanol(df: pd.DataFrame, destino: Path) -> Path:
    d = df.sort_values("paridade", ascending=False)
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.barh(d.uf, d.paridade * 100, color=[VERDE if c else CINZA for c in d.compensa_etanol])
    ax.axvline(LIMITE_PARIDADE * 100, color=VERMELHO, ls="--", lw=1)
    ax.text(LIMITE_PARIDADE * 100, len(d) - 0.2, " limite 70%", color=VERMELHO, fontsize=8, va="bottom")
    for y, v in enumerate(d.paridade * 100):
        ax.text(v + 0.3, y, f"{v:.0f}%", va="center", fontsize=7.5)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_xlim(d.paridade.min() * 100 - 5, d.paridade.max() * 100 + 5)
    n = int(d.compensa_etanol.sum())
    ax.set_title(f"Etanol / gasolina por estado: em verde, onde o etanol compensa ({n} UFs)")
    ax.grid(axis="y", visible=False)
    arq = destino / "paridade_etanol.png"
    fig.savefig(arq)
    plt.close(fig)
    return arq
