"""
Baixa os resumos semanais do Levantamento de Preços de Combustíveis (LPC) da ANP.

A ANP publica um .xlsx por semana nesta página:
https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas

O nome dos arquivos não segue um padrão fixo (às vezes "2026_10_18-2026_10_24",
às vezes "2026-10-04_2026-10-10"), então em vez de montar a URL eu leio os links
direto da página. Fica mais robusto a mudança de nome.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import requests

PAGINA_LPC = (
    "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/"
    "levantamento-de-precos-de-combustiveis-ultimas-semanas-pesquisadas"
)
HEADERS = {"User-Agent": "relatorio-automatico-combustiveis (projeto de portfolio)"}
PADRAO_LINK = re.compile(r'href="([^"]*resumo_semanal_lpc[^"]*\.xlsx)"', re.IGNORECASE)


def listar_resumos(html: str) -> list[str]:
    """Links dos resumos semanais, do mais recente para o mais antigo, sem repetir."""
    vistos, links = set(), []
    for link in PADRAO_LINK.findall(html):
        if link.startswith("/"):
            link = "https://www.gov.br" + link
        if link not in vistos:
            vistos.add(link)
            links.append(link)
    return links


def _get(url: str, tentativas: int = 3) -> requests.Response:
    for i in range(tentativas):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == tentativas - 1:
                raise
            time.sleep(5 * (i + 1))  # site do governo às vezes oscila
    raise RuntimeError("inalcançável")


def baixar_semanas(destino: Path, n_semanas: int = 12) -> list[Path]:
    """Baixa os N resumos mais recentes para `destino`. Arquivos já baixados são reaproveitados."""
    destino.mkdir(parents=True, exist_ok=True)
    links = listar_resumos(_get(PAGINA_LPC).text)[:n_semanas]
    if not links:
        raise RuntimeError("Nenhum resumo semanal encontrado na página da ANP (o layout mudou?)")

    arquivos = []
    for url in links:
        arq = destino / url.rsplit("/", 1)[-1]
        if not arq.exists():
            arq.write_bytes(_get(url).content)
            print(f"  baixado  {arq.name}")
        else:
            print(f"  em cache {arq.name}")
        arquivos.append(arq)
    return arquivos
