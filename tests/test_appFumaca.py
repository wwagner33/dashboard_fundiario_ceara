"""Testes de fumaça do app completo com streamlit.testing.v1.AppTest.

Cada página roda com a API do miniserver simulada, sem navegador e sem backend real.
"""
import copy
import re

import pytest
from streamlit.testing.v1 import AppTest

from modules import config, navegacao
from tests.conftest import GEOJSON_MUNICIPIOS, criarResponderApi

TODAS = re.compile("^" + re.escape(config.DATA_SERVICE_URL))


def _novoApp(pagina=None):
    at = AppTest.from_file("app.py", default_timeout=60)
    if pagina:
        at.session_state[navegacao.CHAVE_SESSAO] = pagina
    return at


@pytest.mark.parametrize("pagina", [p.chave for p in navegacao.PAGINAS])
def test_paginaRenderizaSemExcecao(miniserverSimulado, pagina):
    at = _novoApp(pagina)
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_paginaInicialPadraoEOInicioSemBotaoDeAcesso(miniserverSimulado):
    at = _novoApp()
    at.run()
    assert at.session_state[navegacao.CHAVE_SESSAO] == "inicio"
    assert not [b for b in at.button if "Acessar a plataforma" in (b.label or "")]


def test_menuTemTodasAsPaginasNaOrdem(miniserverSimulado):
    at = _novoApp()
    at.run()
    assert [b.label for b in at.sidebar.button] == [p.rotulo for p in navegacao.PAGINAS]


def test_clicarNoMenuTrocaDePagina(miniserverSimulado):
    at = _novoApp()
    at.run()
    at.button(key="menu-sobre").click().run()
    assert at.session_state[navegacao.CHAVE_SESSAO] == "sobre"
    assert not at.exception


@pytest.mark.parametrize("pagina", ["inicio", "sobre"])
def test_paginasInstitucionaisNaoChamamAApi(miniserverSimulado, pagina):
    _novoApp(pagina).run()
    assert miniserverSimulado.call_count == 0


def test_predominanciaComMunicipioSemLotes(requests_mock):
    # Regressão do bug B2 no app completo: sobral não tem nenhum lote.
    limites = copy.deepcopy(GEOJSON_MUNICIPIOS)
    sobral = copy.deepcopy(limites["features"][0])
    sobral["properties"]["nome_municipio"] = "sobral"
    limites["features"].append(sobral)
    base = criarResponderApi()

    def responder(request, context):
        if request.path.rstrip("/") == "/geojson_muni":
            context.status_code = 200
            return limites
        return base(request, context)

    requests_mock.get(TODAS, json=responder)
    at = _novoApp("predominancia")
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_falhaDaApiMostraMensagemSemDetalheInterno(requests_mock):
    requests_mock.get(TODAS, status_code=500)
    at = _novoApp("graficos")
    at.run()
    assert not at.exception
    assert at.error and "Não foi possível carregar os dados" in at.error[0].value
    assert config.DATA_SERVICE_URL not in at.error[0].value


def test_cssDoMenuDestacaAPaginaAtiva():
    css = navegacao.cssDoMenu("sobre")
    assert ".st-key-menu-sobre button" in css
    assert navegacao.COR_BOTAO_ATIVO in css
