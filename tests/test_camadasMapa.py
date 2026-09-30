"""Testes de modules/camadasMapa.py: camadas compartilhadas entre as páginas."""
import folium
import pytest

from modules import camadasMapa
from modules.constantes import NAO_DISPONIVEL
from tests.conftest import GEOJSON_ASSENTAMENTOS, GEOJSON_MUNICIPIOS, feicaoAssentamento


@pytest.mark.parametrize("valor, esperado", [
    (None, NAO_DISPONIVEL), (float("nan"), NAO_DISPONIVEL), ("", NAO_DISPONIVEL), ("   ", NAO_DISPONIVEL),
    ("nan", NAO_DISPONIVEL), ("None", NAO_DISPONIVEL), ("null", NAO_DISPONIVEL), ("Fortaleza", "Fortaleza"), (42, 42),
])
def test_formatarValor(valor, esperado):
    assert camadasMapa.formatarValor(valor) == esperado


def _html(mapa):
    return mapa.get_root().render()


def test_assentamentosDeUmSoTipoRenderizam():
    # Regressão do bug B5: o grupo do tipo ausente não pode ser criado vazio.
    mapa = folium.Map()
    geojson = {"type": "FeatureCollection", "features": [feicaoAssentamento("estadual", "CE0001")]}
    camadasMapa.adicionarCamadasAssentamentos(mapa, geojson)
    camadasMapa.adicionarControles(mapa)
    html = _html(mapa)
    assert "Assentamentos Estaduais" in html
    assert "Assentamentos Federais" not in html


def test_assentamentosVaziosNaoCriamCamada():
    mapa = folium.Map()
    camadasMapa.adicionarCamadasAssentamentos(mapa, {"type": "FeatureCollection", "features": []})
    assert "Assentamentos" not in _html(mapa)


def test_assentamentosComMarcadoresUsamClusterEEscapamTexto():
    mapa = folium.Map()
    geojson = {"type": "FeatureCollection", "features": [feicaoAssentamento("federal", "CE9", nome="<script>x</script>")]}
    camadasMapa.adicionarCamadasAssentamentos(mapa, geojson, comMarcadores=True)
    html = _html(mapa)
    assert "markerClusterGroup" in html
    assert "<script>x</script>" not in html


def test_assentamentosNaoAlteramOGeojsonOriginal():
    antes = GEOJSON_ASSENTAMENTOS["features"][0]["properties"].copy()
    camadasMapa.adicionarCamadasAssentamentos(folium.Map(), GEOJSON_ASSENTAMENTOS)
    assert GEOJSON_ASSENTAMENTOS["features"][0]["properties"] == antes


def test_camadaDeMunicipiosEscapaONome():
    geojson = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"nome_municipio": "<img src=x onerror=alert(1)>"},
         "geometry": GEOJSON_MUNICIPIOS["features"][0]["geometry"]}
    ]}
    mapa = folium.Map()
    camadasMapa.adicionarCamadaMunicipios(mapa, geojson)
    assert "<img src=x" not in _html(mapa)


def test_camadaDeMunicipiosAceitaEstiloProprio():
    mapa = folium.Map()
    camadasMapa.adicionarCamadaMunicipios(mapa, GEOJSON_MUNICIPIOS, estilo={"color": "#003366"})
    assert "#003366" in _html(mapa)


def test_rotuloLegendaCirculo():
    assert "<circle" in camadasMapa.rotuloLegenda("#fff", "Categoria", forma="circulo")


def test_renderizarMapaUsaALarguraDoConteiner(monkeypatch):
    chamadas = {}
    monkeypatch.setattr(camadasMapa, "st_folium", lambda mapa, **kw: chamadas.update(kw) or {})
    camadasMapa.renderizarMapa(folium.Map(), altura=600, retornar=["last_active_drawing"], chave="x")
    assert chamadas == {"height": 600, "use_container_width": True, "returned_objects": ["last_active_drawing"], "key": "x"}
