"""
Testes com a amostra real (12 semanas de out/2026) recriada no layout da ANP.
    pytest -q
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "src"), str(RAIZ / "tests" / "fixtures"), str(RAIZ)]

import indicadores as ind  # noqa: E402
from coleta import listar_resumos  # noqa: E402
from gerar_xlsx import gerar  # noqa: E402
from leitura import ler_aba, ler_semanas  # noqa: E402
from resumo import gerar_resumo, resumo_automatico  # noqa: E402


@pytest.fixture(scope="module")
def dados(tmp_path_factory):
    arquivos = gerar(tmp_path_factory.mktemp("raw"))
    return ler_semanas(arquivos)


def test_listar_resumos_pega_os_dois_padroes_de_nome():
    html = '''
      <a href="https://www.gov.br/x/arquivos-lpc/2026/resumo_semanal_lpc_2026_10_18-2026_10_24.xlsx">a</a>
      <a href="https://www.gov.br/x/arquivos-lpc/2026/revendas_lpc_2026_10_18-2026_10_24.xlsx">b</a>
      <a href="/x/arquivos-lpc/2026/resumo_semanal_lpc_2026-10-04_2026-10-10.xlsx">c</a>
      <a href="https://www.gov.br/x/arquivos-lpc/2026/resumo_semanal_lpc_2026_10_18-2026_10_24.xlsx">repetido</a>
    '''
    links = listar_resumos(html)
    assert len(links) == 2
    assert links[1].startswith("https://www.gov.br/")
    assert all("revendas" not in l for l in links)


def test_leitura_acha_cabecalho_e_converte_datas(tmp_path):
    arq = gerar(tmp_path)[0]
    br = ler_aba(arq, "BRASIL")
    assert br["data_inicial"].iloc[0] == pd.Timestamp("2026-10-18")
    assert br["preco_medio"].dtype.kind == "f"
    assert set(ind.PRODUTOS) <= set(br["produto"])


def test_semanas_sem_duplicidade(dados):
    br, est = dados
    assert br.duplicated(["data_inicial", "produto"]).sum() == 0
    assert br["data_inicial"].nunique() == 12
    assert est.duplicated(["data_inicial", "estado", "produto"]).sum() == 0


def test_resumo_nacional_bate_com_a_planilha(dados):
    br, _ = dados
    nac = ind.resumo_nacional(br).set_index("produto")
    assert nac.loc["Gasolina comum", "preco_atual"] == pytest.approx(6.49)
    assert nac.loc["Gasolina comum", "var_semana_pct"] == pytest.approx(100 * (6.49 / 6.53 - 1))
    assert nac.loc["Diesel S10", "var_janela_pct"] == pytest.approx(100 * (7.32 / 6.94 - 1))


def test_serie_comeca_em_zero(dados):
    br, _ = dados
    assert (ind.serie_nacional(br).iloc[0] == 0).all()


def test_paridade(dados):
    _, est = dados
    par = ind.paridade_etanol(est)
    sp = par.set_index("uf").loc["SP"]
    assert sp.paridade == pytest.approx(3.89 / 6.35)
    assert bool(sp.compensa_etanol)
    assert (par.paridade.diff().dropna() >= 0).all()  # ordenado


def test_estados_tem_27_ufs_na_gasolina(dados):
    _, est = dados
    gas = ind.precos_estados(est, "GASOLINA COMUM")
    assert len(gas) == 27
    assert gas.uf.notna().all()


def test_resumo_sem_chave_usa_texto_automatico(dados, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    texto, origem = gerar_resumo(ind.destaques(*dados))
    assert origem == "automatico"
    assert "R$ 6,49" in texto


def test_falha_da_ia_cai_no_automatico(dados, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "chave-invalida")
    import resumo
    monkeypatch.setattr(resumo, "resumo_ia", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    texto, origem = gerar_resumo(ind.destaques(*dados))
    assert origem == "automatico" and texto == resumo_automatico(ind.destaques(*dados))


def test_pipeline_completo_offline(tmp_path):
    import main
    pasta = main.main(["--offline", "--saida", str(tmp_path)])
    for nome in ["relatorio.xlsx", "relatorio.pdf", "RESUMO.md", "tendencia_nacional.png",
                 "gasolina_por_estado.png", "paridade_etanol.png"]:
        assert (pasta / nome).stat().st_size > 0, nome
    assert (tmp_path / "ultimo" / "relatorio.pdf").exists()
    abas = pd.ExcelFile(pasta / "relatorio.xlsx").sheet_names
    assert abas == ["Resumo", "Histórico Brasil", "Estados (semana)", "Paridade etanol"]
