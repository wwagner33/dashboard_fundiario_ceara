"""Testes de modules/paginaEscolasCampo.py: dados fixos, filtro e estatísticas."""
import re

import pytest

from modules import paginaEscolasCampo as pe


def test_escolasTemCamposObrigatorios():
    campos = {"crede", "nome_municipio", "nome_municipio_original", "assentamento", "nome_escola", "latitude", "longitude"}
    for escola in pe.ESCOLAS_DO_CAMPO:
        assert campos <= escola.keys()


def test_nomesDeMunicipioSeguemOFormatoNormalizado():
    for escola in pe.ESCOLAS_DO_CAMPO:
        assert re.fullmatch(r"[a-z_]+", escola["nome_municipio"]), escola["nome_municipio"]


@pytest.mark.parametrize("municipio", pe.listarMunicipiosComEscolas())
def test_cadaMunicipioDaListaTemAoMenosUmaEscola(municipio):
    # Regressão do bug B1: "mons. Tabosa" não encontrava a própria escola.
    escolas = pe.filtrarEscolas(municipio)
    assert escolas
    assert pe.calcularEstatisticas(escolas)["porCrede"]


def test_listaOrdenadaPeloNomeExibido():
    nomes = [pe.NOMES_MUNICIPIOS[chave] for chave in pe.listarMunicipiosComEscolas()]
    assert nomes == sorted(nomes)


def test_estatisticasVaziasTemPorCrede():
    assert pe.calcularEstatisticas([]) == {"total": 0, "porCrede": {}}


def test_estatisticasAgrupamPorCrede():
    escolas = [{"crede": 2}, {"crede": 2}, {"crede": 3}]
    assert pe.calcularEstatisticas(escolas) == {"total": 3, "porCrede": {2: 2, 3: 1}}
