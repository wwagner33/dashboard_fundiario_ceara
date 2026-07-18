"""Smoke tests de UI: app.py

Usa streamlit.testing.v1.AppTest para executar cada página do dashboard com
dados mockados (via fixture `mocked_miniserver`), garantindo que renderiza
sem lançar exceção -- sem precisar de um navegador real nem de um backend
terraGeoDataMiniServer real.

Observação: app.py carrega dados fundiários e municípios no nível de módulo
(fora de qualquer função de página), então TODA página exercita
load_csv_data/validate_data/load_municipios, não só a página selecionada.
"""
import pytest
from streamlit.testing.v1 import AppTest


PAGES = [
    "Inicio",
    "Gráficos",
    "Mapa de Predominância",
    "Mapa da Malha Fundiária",
    "Mapa de Concentração Fundiária",
    "Mapa de Assentamento",
    "Mapa Hidrografico",
    "Mapa Escolas do Campo",
    "Sobre",
]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_exception(mocked_miniserver, page):
    at = AppTest.from_file("app.py", default_timeout=30)
    at.session_state["current_page"] = page
    at.run()
    assert not at.exception, [str(e) for e in at.exception]


def test_landing_page_button_navigates_to_graficos(mocked_miniserver):
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert at.session_state["current_page"] == "Inicio"
    assert not at.exception

    # Clica no botão "Acessar a plataforma Terra.Ce" da landing page
    botoes = [b for b in at.button if "Acessar a plataforma" in (b.label or "")]
    assert botoes, "Botão de acesso não encontrado na landing page"
    botoes[0].click().run()

    assert at.session_state["current_page"] == "Gráficos"
    assert not at.exception


def test_sidebar_tem_todos_os_botoes_de_navegacao(mocked_miniserver):
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    labels = {b.label for b in at.sidebar.button}
    esperados = {
        "Início", "Gráficos e Quadros", "Mapa de Predominância",
        "Mapa da Malha Fundiária", "Mapa de Concentração Fundiária",
        "Mapa de Assentamentos", "Mapa Hidrográfico",
        "Mapa Escolas do Campo", "Sobre",
    }
    assert esperados.issubset(labels)
