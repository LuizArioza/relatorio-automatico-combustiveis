"""
Resumo executivo da semana.

Duas formas:
  - automático (padrão): texto montado por regras a partir dos indicadores
  - IA (opcional): se a variável ANTHROPIC_API_KEY existir, um modelo escreve o resumo
    usando SÓ os números calculados. Se a chamada falhar por qualquer motivo, volta
    para o texto automático. O relatório nunca deixa de sair por causa da IA.
"""
from __future__ import annotations

import json
import os

import requests

MODELO_PADRAO = "claude-haiku-5-5"


def _brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v: float) -> str:
    sinal = "+" if v > 0 else ""
    return f"{sinal}{v:.1f}%".replace(".", ",")


def _tendencia(v: float) -> str:
    if abs(v) < 0.3:
        return "ficou estável"
    return "subiu" if v > 0 else "caiu"


def resumo_automatico(d: dict) -> str:
    nac = {r["produto"]: r for r in d["nacional"]}
    linhas = []

    g = nac.get("Gasolina comum")
    if g:
        linhas.append(
            f"A gasolina comum {_tendencia(g['var_semana_pct'])} na semana: média nacional de "
            f"{_brl(g['preco_atual'])}/l ({_pct(g['var_semana_pct'])}), "
            f"{_pct(g['var_janela_pct'])} em {g['semanas_janela']} semanas."
        )

    maior = max(d["nacional"], key=lambda r: r["var_janela_pct"])
    if maior["var_janela_pct"] > 1:
        unidade = maior["unidade"].replace("R$", "")
        linhas.append(
            f"Maior alta em {maior['semanas_janela']} semanas: {maior['produto']} "
            f"({_pct(maior['var_janela_pct'])}), hoje a {_brl(maior['preco_atual'])}{unidade}."
        )

    if "gasolina_mais_barata" in d:
        b, c = d["gasolina_mais_barata"], d["gasolina_mais_cara"]
        linhas.append(
            f"Gasolina mais barata em {b['uf']} ({_brl(b['preco_medio'])}) e mais cara em "
            f"{c['uf']} ({_brl(c['preco_medio'])}), diferença de {_brl(c['preco_medio'] - b['preco_medio'])} por litro."
        )
    if "gasolina_maior_alta" in d:
        a = d["gasolina_maior_alta"]
        linhas.append(f"Maior alta semanal da gasolina: {a['uf']} ({_pct(a['var_semana_pct'])}).")

    if d.get("ufs_etanol_compensa") is not None:
        ufs = d["ufs_etanol_compensa"]
        p = d["melhor_paridade"]
        linhas.append(
            f"O etanol compensa (até 70% do preço da gasolina) em {len(ufs)} estados; "
            f"a melhor relação é em {p['uf']} ({p['paridade'] * 100:.0f}%)."
        )
    return " ".join(linhas)


def _para_json(d: dict) -> str:
    def conv(x):
        if hasattr(x, "isoformat"):
            return x.isoformat()[:10]
        if isinstance(x, float):
            return round(x, 3)
        return x
    limpo = json.loads(json.dumps(d, default=conv))
    return json.dumps(limpo, ensure_ascii=False, indent=1)


def resumo_ia(d: dict, api_key: str, modelo: str = MODELO_PADRAO) -> str:
    prompt = (
        "Você é analista de dados e escreve o resumo executivo de um relatório semanal de "
        "preços de combustíveis no Brasil (fonte: ANP). Use SOMENTE os números do JSON abaixo, "
        "sem inventar dados nem causas. Escreva em português, em 3 a 4 frases curtas, para um "
        "gestor que tem 30 segundos: o que mudou na semana, o que chama atenção e um ponto de "
        "atenção. Valores em reais com vírgula decimal.\n\n" + _para_json(d)
    )
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": modelo, "max_tokens": 400, "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    r.raise_for_status()
    texto = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    if not texto.strip():
        raise ValueError("resposta vazia")
    return texto.strip()


def gerar_resumo(d: dict) -> tuple[str, str]:
    """Retorna (texto, origem) onde origem é 'ia' ou 'automatico'."""
    chave = os.getenv("ANTHROPIC_API_KEY")
    if chave:
        try:
            return resumo_ia(d, chave, os.getenv("ANTHROPIC_MODEL", MODELO_PADRAO)), "ia"
        except Exception as e:  # noqa: BLE001 - qualquer falha da IA cai no texto automático
            print(f"  IA indisponível ({type(e).__name__}), usando resumo automático")
    return resumo_automatico(d), "automatico"
