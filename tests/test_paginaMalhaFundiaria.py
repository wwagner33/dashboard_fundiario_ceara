"""Testes de modules/paginaMalhaFundiaria.py: LGPD e preparação dos polígonos."""
from modules import paginaMalhaFundiaria as pm
from modules.constantes import CENTRO_CEARA
from modules.privacidade import TEXTO_NOME_PROTEGIDO
from tests.conftest import criarLote, geojsonLotes


def test_nomeDePessoaFisicaNaoChegaAoMapa():
    geojson = geojsonLotes([criarLote(nome_proprietario="Maria Joaquina de Amaral")])
    grupos = pm.prepararLotesParaMapa(geojson)
    feicao = grupos["Pequena Propriedade"]["features"][0]
    assert feicao["properties"]["nome_proprietario"] == TEXTO_NOME_PROTEGIDO
    centro = pm.obterCentroMapa(geojson)
    html = pm.criarMapaMalha(grupos, {"type": "FeatureCollection", "features": []}, centro).get_root().render()
    assert "Maria Joaquina" not in html
    assert "protegido pela LGPD" in html  # o folium grava acentos como \\uXXXX


def test_nomeDePessoaJuridicaEExibido():
    geojson = geojsonLotes([criarLote(nome_proprietario="Agropecuária Boa Vista Ltda")])
    feicao = pm.prepararLotesParaMapa(geojson)["Pequena Propriedade"]["features"][0]
    assert feicao["properties"]["nome_proprietario"] == "Agropecuária Boa Vista Ltda"


def test_somenteCamposDoTooltipSeguemParaOMapa():
    geojson = geojsonLotes([criarLote(cpf_proprietario="000.000.000-00")])
    propriedades = pm.prepararLotesParaMapa(geojson)["Pequena Propriedade"]["features"][0]["properties"]
    assert set(propriedades) == {campo for campo, _ in pm.CAMPOS_TOOLTIP}


def test_textoDoImovelEEscapado():
    geojson = geojsonLotes([criarLote(imovel="<script>alert(1)</script>")])
    propriedades = pm.prepararLotesParaMapa(geojson)["Pequena Propriedade"]["features"][0]["properties"]
    assert propriedades["imovel"].startswith("&lt;script&gt;")


def test_agrupaPorCategoriaEIgnoraCategoriaDesconhecida():
    geojson = geojsonLotes([
        criarLote(categoria="Grande Propriedade"), criarLote(categoria="Grande Propriedade"),
        criarLote(categoria="Categoria Estranha"), criarLote(categoria=None),
    ])
    grupos = pm.prepararLotesParaMapa(geojson)
    assert list(grupos) == ["Grande Propriedade"]
    assert len(grupos["Grande Propriedade"]["features"]) == 2


def test_centroDoMapa():
    assert pm.obterCentroMapa(geojsonLotes([criarLote()])) == [-3.8, -38.6]
    assert pm.obterCentroMapa({"features": []}) == CENTRO_CEARA
