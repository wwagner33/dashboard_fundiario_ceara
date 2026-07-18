"""Fixtures compartilhadas para a suíte de testes do dashboard_fundiario_ceara.

Importante:
- Os testes aqui NUNCA devem depender de um terraGeoDataMiniServer real rodando.
  Toda comunicação HTTP é interceptada via `requests_mock`.
- Vários módulos (data_loader, mapa_assentamento, mapa_escolas, mapa_reservatorios)
  leem `st.secrets["JWT_SECRET"]` no nível de módulo. Isso funciona porque os
  testes rodam com cwd = dashboard_fundiario_ceara/, onde existe
  .streamlit/secrets.toml com um valor de teste.
- `st.cache_data`/`st.cache_resource` mantêm cache global entre chamadas de
  função (não por teste), então limpamos os caches do Streamlit antes de cada
  teste para evitar contaminação entre casos de teste.
"""
import re

import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def _clear_streamlit_state():
    """Evita que cache/sessão de um teste vaze para o próximo."""
    st.cache_data.clear()
    st.cache_resource.clear()
    try:
        st.session_state.clear()
    except Exception:
        pass
    yield
    st.cache_data.clear()
    st.cache_resource.clear()


# ---------------------------------------------------------------------------
# Dados de exemplo usados pelo "servidor" (miniserver) simulado
# ---------------------------------------------------------------------------

SAMPLE_LOTE = {
    "imovel": "Fazenda Teste",
    "data_criacao_lote": "2020-01-01",
    "numero_incra": "123.456",
    "numero_lote": "1",
    "area": 10.0,
    "situacao_juridica": "Regular",
    "regiao_administrativa": "Regiao Teste",
    "nome_municipio_original": "Fortaleza",
    "nome_distrito": "Centro",
    "ponto_de_referencia": "",
    "categoria": "Pequena Propriedade",
    "geometry": None,
    "nome_municipio": "fortaleza",
    "modulo_fiscal": 5.0,
    "lote_id": "1",
    "nome_proprietario": "Fulano de Tal",
}


def make_lote(**overrides):
    lote = dict(SAMPLE_LOTE)
    lote.update(overrides)
    return lote


SAMPLE_MUNI_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"nome_municipio": "fortaleza"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-38.6, -3.8], [-38.5, -3.8], [-38.5, -3.7], [-38.6, -3.7], [-38.6, -3.8]]],
            },
        }
    ],
}

def _assentamento_feature(tipo, cd_sipra):
    return {
        "type": "Feature",
        "properties": {
            "cd_sipra": cd_sipra,
            "tipo_assentamento": tipo,
            "nome_assentamento": "Assentamento Teste",
            "nome_municipio_original": "Fortaleza",
            "num_familias": 12,
            "forma_obtecao": "Desapropriação",
            "area": 100.5,
            "perimetro": 10.2,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-38.6, -3.8], [-38.5, -3.8], [-38.5, -3.7], [-38.6, -3.7], [-38.6, -3.8]]],
        },
    }


# Inclui os dois tipos (estadual e federal): ver test_mapa_reservatorios.py::
# test_adicionar_camadas_assentamentos_quebra_com_subconjunto_vazio -- quando
# apenas um tipo está presente, o folium.GeoJsonTooltip do outro grupo (vazio)
# lança AssertionError ao renderizar. Manter os dois tipos aqui evita que esse
# bug de produção derrube os smoke tests de outras páginas.
SAMPLE_ASSENTAMENTOS_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        _assentamento_feature("estadual", "CE0001"),
        _assentamento_feature("federal", "CE0002"),
    ],
}

SAMPLE_RESERVATORIOS_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "id_sagreh": "1",
                "nome": "Açude Teste",
                "proprietario": "Estado",
                "gerencia": "COGERH",
                "reg_hidrog": "Regiao 1",
                "nome_municipio_original": "Fortaleza",
                "ano_constr": "1990",
                "ri": "Rio Teste",
                "o_barrad": "Sim",
                "area_ha": 50.0,
                "capacid_m3": 1000.0,
            },
            "geometry": {"type": "Point", "coordinates": [-38.55, -3.75]},
        }
    ],
}


def api_responder_factory():
    """Cria uma função callback do requests_mock que simula os principais
    endpoints do terraGeoDataMiniServer, independente do prefixo (com ou sem
    "/api") usado por cada módulo do dashboard."""

    def _responder(request, context):
        path = request.path.rstrip("/")
        if path.startswith("/api"):
            path = path[len("/api"):]

        context.status_code = 200

        if path == "/regioes":
            return {"regioes": ["Regiao Teste"]}
        if path == "/dados_fundiarios":
            return [SAMPLE_LOTE]
        if path == "/version":
            return {"data_version": "test-1.0.0"}
        if path == "/municipios_todos":
            return {"municipios": ["fortaleza"]}
        if path == "/geojson_muni":
            return SAMPLE_MUNI_GEOJSON
        if path == "/municipios":
            return {"municipios": ["fortaleza"]}
        if path == "/geojson":
            return SAMPLE_MUNI_GEOJSON
        if path == "/geojson_assentamentos":
            return SAMPLE_ASSENTAMENTOS_GEOJSON
        if path == "/geojson_reservatorios":
            return SAMPLE_RESERVATORIOS_GEOJSON
        if path == "/assentamentos_municipios":
            return {"municipios": ["fortaleza"]}
        if path == "/reservatorios_municipios":
            return {"municipios": ["fortaleza"]}

        context.status_code = 404
        return {}

    return _responder


@pytest.fixture
def mocked_miniserver(requests_mock):
    """Intercepta toda chamada HTTP para localhost:8000 (com ou sem /api) e
    devolve respostas canônicas simulando o terraGeoDataMiniServer.

    Uso: passe este fixture para qualquer teste que precise que
    `load_csv_data`, `load_municipios`, `render_view_*`, etc. funcionem sem
    bater num backend real.
    """
    responder = api_responder_factory()
    requests_mock.get(re.compile(r"^http://localhost:8000"), json=responder)
    return requests_mock
