"""Fixtures compartilhadas da suíte de testes do dashboard_fundiario_ceara.

- Nenhum teste depende de um terraGeoDataMiniServer real: o HTTP é
  interceptado com ``requests_mock``.
- ``JWT_SECRET`` vem de uma variável de ambiente de teste definida aqui, antes
  da importação dos módulos, então a suíte não precisa do ``secrets.toml``.
- Os caches do Streamlit e o token JWT em memória são limpos antes e depois de
  cada teste, para que um caso não contamine o outro.
"""
import os
import re

os.environ.setdefault("JWT_SECRET", "segredo-de-teste-com-mais-de-32-bytes-0123456789")

import pytest  # noqa: E402
import streamlit as st  # noqa: E402

from modules import apiCliente, config, repositorio  # noqa: E402


@pytest.fixture(autouse=True)
def _versaoDosDados(request, monkeypatch):
    """Desliga a consulta a /versao_dados, exceto com o miniserver simulado ou o marcador comVersao.

    Assim os testes que registram só os endpoints que usam não precisam
    registrar também /versao_dados.
    """
    monkeypatch.setattr(repositorio, "_versaoConhecida", None)
    if "miniserverSimulado" not in request.fixturenames and not request.node.get_closest_marker("comVersao"):
        monkeypatch.setattr(repositorio, "carregarVersaoDados", lambda: "")


@pytest.fixture(autouse=True)
def _limparEstadoStreamlit():
    st.cache_data.clear()
    st.cache_resource.clear()
    apiCliente.descartarToken()
    try:
        st.session_state.clear()
    except Exception:
        pass
    yield
    st.cache_data.clear()
    st.cache_resource.clear()
    apiCliente.descartarToken()


# ---------------------------------------------------------------------------
# Dados de exemplo servidos pelo miniserver simulado
# ---------------------------------------------------------------------------

LOTE_EXEMPLO = {
    "imovel": "Fazenda Teste",
    "data_criacao_lote": "2020-01-01",
    "numero_incra": "123.456",
    "numero_lote": "1",
    "numero_titulo": "10",
    "area": 10.0,
    "situacao_juridica": "Regular",
    "regiao_administrativa": "Regiao Teste",
    "nome_municipio_original": "Fortaleza",
    "nome_distrito": "Centro",
    "categoria": "Pequena Propriedade",
    "nome_municipio": "fortaleza",
    "modulo_fiscal": 5.0,
    "nome_proprietario": "Pessoa física (protegido pela LGPD)",
    "id_proprietario": "0123456789abcdef0123456789abcdef",
}


def criarLote(**alteracoes):
    lote = dict(LOTE_EXEMPLO)
    lote.update(alteracoes)
    return lote


QUADRADO = {
    "type": "Polygon",
    "coordinates": [[[-38.6, -3.8], [-38.5, -3.8], [-38.5, -3.7], [-38.6, -3.7], [-38.6, -3.8]]],
}

GEOJSON_MUNICIPIOS = {
    "type": "FeatureCollection",
    "features": [{"type": "Feature", "properties": {"nome_municipio": "fortaleza"}, "geometry": QUADRADO}],
}


def feicaoAssentamento(tipo, cdSipra, nome="Assentamento Teste"):
    return {
        "type": "Feature",
        "properties": {
            "cd_sipra": cdSipra,
            "tipo_assentamento": tipo,
            "nome_assentamento": nome,
            "nome_municipio": "fortaleza",
            "nome_municipio_original": "Fortaleza",
            "num_familias": 12,
            "forma_obtecao": "Desapropriação",
            "area": 100.5,
            "perimetro": 10.2,
        },
        "geometry": QUADRADO,
    }


GEOJSON_ASSENTAMENTOS = {
    "type": "FeatureCollection",
    "features": [feicaoAssentamento("estadual", "CE0001"), feicaoAssentamento("federal", "CE0002")],
}

GEOJSON_RESERVATORIOS = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "id_sagreh": "1", "nome": "Açude Teste", "proprietario": "Estado", "gerencia": "COGERH",
                "reg_hidrog": "Regiao 1", "nome_municipio": "fortaleza", "nome_municipio_original": "Fortaleza",
                "ano_constr": "1990", "ri": "Rio Teste", "o_barrad": "Sim", "area_ha": 50.0, "capacid_m3": 1000.0,
            },
            "geometry": QUADRADO,
        }
    ],
}


def geojsonLotes(lotes):
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": dict(lote), "geometry": QUADRADO} for lote in lotes
    ]}


def criarResponderApi(lotes=None):
    """Callback do requests_mock que simula os endpoints do miniserver."""
    lotes = lotes if lotes is not None else [LOTE_EXEMPLO]

    def responder(request, context):
        caminho = request.path.rstrip("/")
        context.status_code = 200
        if caminho == "/versao_dados":
            return {"versao": "2026-09-30 10:00:00", "cargas": []}
        if caminho == "/regioes":
            return {"regioes": ["Regiao Teste"]}
        if caminho == "/municipios":
            return {"municipios": ["fortaleza"]}
        if caminho == "/dados_fundiarios":
            return lotes
        if caminho == "/geojson_muni":
            return GEOJSON_MUNICIPIOS
        if caminho == "/geojson":
            return geojsonLotes(lotes)
        if caminho == "/geojson_assentamentos":
            return GEOJSON_ASSENTAMENTOS
        if caminho == "/assentamentos_municipios":
            return {"municipios": ["fortaleza"]}
        if caminho == "/geojson_reservatorios":
            return GEOJSON_RESERVATORIOS
        if caminho == "/reservatorios_municipios":
            return {"municipios": ["fortaleza"]}
        context.status_code = 404
        return {"detail": "não encontrado"}

    return responder


def url(endpoint):
    return f"{config.DATA_SERVICE_URL}/{endpoint}"


@pytest.fixture
def miniserverSimulado(requests_mock):
    """Intercepta toda chamada ao miniserver e devolve as respostas de exemplo."""
    requests_mock.get(re.compile("^" + re.escape(config.DATA_SERVICE_URL)), json=criarResponderApi())
    return requests_mock
