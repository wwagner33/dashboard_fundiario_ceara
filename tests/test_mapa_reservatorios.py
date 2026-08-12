"""Testes de modules/mapa_reservatorios.py: formatação, estatísticas
(lógica pura) e chamadas HTTP mockadas."""
import pytest
import requests

from modules import mapa_reservatorios as mr
from tests.conftest import SAMPLE_RESERVATORIOS_GEOJSON


# ---------------------------------------------------------------------------
# formatar_valor (lógica pura, idêntica em todos os módulos mapa_*)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("valor, esperado", [
    (None, "Não Disponível"),
    (float("nan"), "Não Disponível"),
    ("null", "Não Disponível"),
    ("Açude Teste", "Açude Teste"),
])
def test_formatar_valor(valor, esperado):
    assert mr.formatar_valor(valor) == esperado


# ---------------------------------------------------------------------------
# obter_estatisticas_reservatorios (lógica pura)
# ---------------------------------------------------------------------------

def test_obter_estatisticas_reservatorios_sem_dados():
    stats = mr.obter_estatisticas_reservatorios(None)
    assert stats == {"total": 0, "cap_total_m³": 0, "area_ha": 0}


def test_obter_estatisticas_reservatorios_soma_capacidade_e_area():
    stats = mr.obter_estatisticas_reservatorios(SAMPLE_RESERVATORIOS_GEOJSON)
    assert stats["total"] == 1
    assert stats["cap_total_m³"] == pytest.approx(1000.0)
    assert stats["area_ha"] == pytest.approx(50.0)


def test_obter_estatisticas_reservatorios_ignora_valores_invalidos():
    geojson = {
        "features": [
            {"properties": {"capacid_m3": "abc", "area_ha": "xyz"}},
        ]
    }
    stats = mr.obter_estatisticas_reservatorios(geojson)
    assert stats["total"] == 1
    assert stats["cap_total_m³"] == 0
    assert stats["area_ha"] == 0


# ---------------------------------------------------------------------------
# carregar_reservatorios / obter_municipios_reservatorios (HTTP mockado)
# ---------------------------------------------------------------------------

def test_carregar_reservatorios_sucesso(mocked_miniserver):
    result = mr.carregar_reservatorios("todos")
    assert result == SAMPLE_RESERVATORIOS_GEOJSON


def test_obter_municipios_reservatorios_sucesso(mocked_miniserver):
    assert mr.obter_municipios_reservatorios() == ["fortaleza"]


def test_obter_municipios_reservatorios_timeout_retorna_lista_vazia(requests_mock):
    requests_mock.get(
        f"{mr.DATA_SERVICE_URL}/reservatorios_municipios",
        exc=requests.exceptions.Timeout,
    )
    assert mr.obter_municipios_reservatorios() == []


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG de produção: quando o GeoJSON de assentamentos filtrado para um "
        "tipo ('estadual' ou 'federal') fica vazio, o FeatureGroup daquele tipo "
        "é um GeoJson sem propriedades, e o folium.GeoJsonTooltip falha ao "
        "renderizar pedindo campos como 'cd_sipra' que não existem em um "
        "GeoDataFrame vazio. Isso derruba render_view_reservatorios_map() e "
        "render_view_escolas_map() sempre que a área filtrada só tem "
        "assentamentos de um único tipo (ex.: um município que só tem "
        "assentamentos federais). Reportado ao invés de corrigido, pois "
        "está fora do escopo desta tarefa de testes (não é modificação "
        "mínima de testabilidade)."
    ),
)
def test_adicionar_camadas_assentamentos_quebra_com_subconjunto_vazio_de_tipo():
    import folium
    from tests.conftest import _assentamento_feature

    # Só assentamentos "estadual": o grupo "federal" fica vazio.
    geojson = {
        "type": "FeatureCollection",
        "features": [_assentamento_feature("estadual", "CE0001")],
    }
    mapa = folium.Map()
    mr.adicionar_camadas_assentamentos(mapa, geojson)
    mapa.get_root().render()  # levanta AssertionError do folium hoje


def test_adicionar_camada_assentamentos_referencia_variavel_inexistente():
    """`adicionar_camada_assentamentos` (função morta, não usada pelo
    render_view_reservatorios_map atual, que usa `adicionar_camadas_assentamentos`)
    referencia `COR_ASSENTAMENTO`, que não existe no módulo -- só
    `CORES_ASSENTAMENTOS` (dict). Isso é uma NameError latente; reportado aqui
    em vez de corrigido, conforme escopo desta tarefa de testes."""
    import folium
    mapa = folium.Map()
    geojson_data = {"features": [{"properties": {}, "geometry": {"type": "Point", "coordinates": [0, 0]}}]}
    with pytest.raises(NameError):
        mr.adicionar_camada_assentamentos(mapa, geojson_data)
