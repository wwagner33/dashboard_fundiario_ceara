"""Testes de modules/mapa_escolas.py: formatação, estatísticas (lógica pura)
e chamadas HTTP mockadas para geojson de municípios/assentamentos."""
import pytest

from modules import mapa_escolas as me
from tests.conftest import SAMPLE_MUNI_GEOJSON


# ---------------------------------------------------------------------------
# formatar_valor (lógica pura)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("valor, esperado", [
    (None, "Não Disponível"),
    (float("nan"), "Não Disponível"),
    ("", "Não Disponível"),
    ("nan", "Não Disponível"),
    ("Fortaleza", "Fortaleza"),
])
def test_formatar_valor(valor, esperado):
    assert me.formatar_valor(valor) == esperado


# ---------------------------------------------------------------------------
# ESCOLAS_DO_CAMPO (dados estáticos) / obter_municipios_com_escolas
# ---------------------------------------------------------------------------

def test_obter_municipios_com_escolas_inclui_todos_e_esta_ordenada():
    municipios = me.obter_municipios_com_escolas()
    assert municipios[0] == "Todos"
    esperado_sem_todos = sorted(set(e["nome_municipio"] for e in me.ESCOLAS_DO_CAMPO))
    assert municipios[1:] == esperado_sem_todos


def test_escolas_do_campo_tem_campos_obrigatorios():
    campos = {"crede", "nome_municipio", "assentamento", "nome_escola", "latitude", "longitude"}
    for escola in me.ESCOLAS_DO_CAMPO:
        assert campos.issubset(escola.keys())


# ---------------------------------------------------------------------------
# obter_estatisticas_escolas (lógica pura)
# ---------------------------------------------------------------------------

def test_obter_estatisticas_escolas_vazio():
    assert me.obter_estatisticas_escolas([]) == {"total": 0}


def test_obter_estatisticas_escolas_agrupa_por_crede():
    escolas = [
        {"crede": 2, "nome_municipio": "a"},
        {"crede": 2, "nome_municipio": "b"},
        {"crede": 3, "nome_municipio": "c"},
    ]
    stats = me.obter_estatisticas_escolas(escolas)
    assert stats["total"] == 3
    assert stats["por_crede"] == {2: 2, 3: 1}


# ---------------------------------------------------------------------------
# carregar_municipios / carregar_assentamentos (chamadas HTTP mockadas)
# ---------------------------------------------------------------------------

def test_carregar_municipios_sucesso(mocked_miniserver):
    result = me.carregar_municipios("todos")
    assert result == SAMPLE_MUNI_GEOJSON


def test_carregar_assentamentos_erro_retorna_none(requests_mock):
    requests_mock.get(
        f"{me.DATA_SERVICE_URL}/geojson_assentamentos",
        status_code=500,
    )
    with pytest.raises(Exception):
        # _fetch_from_api relança a exceção quando não há backup local
        me.carregar_assentamentos("todos")
