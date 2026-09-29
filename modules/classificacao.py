# modules/classificacao.py
"""Classificação dos imóveis rurais pelo tamanho em módulos fiscais (MF).

Faixas: menor que 1 MF, até 4 MF (pequena), até 15 MF (média) e acima de
15 MF (grande). Esta é a única implementação da regra no dashboard.
"""

import numpy as np
import pandas as pd

CATEGORIAS = [
    "Pequena Propriedade < 1 MF",
    "Pequena Propriedade",
    "Média Propriedade",
    "Grande Propriedade",
]
SEM_CLASSIFICACAO = "Sem Classificação"


def classificarPorModuloFiscal(area, moduloFiscal) -> np.ndarray:
    """Devolve a categoria de cada imóvel a partir da área e do módulo fiscal."""
    area = np.asarray(area, dtype=float)
    moduloFiscal = np.asarray(moduloFiscal, dtype=float)
    condicoes = [
        area < moduloFiscal,
        area <= 4 * moduloFiscal,
        area <= 15 * moduloFiscal,
        area > 15 * moduloFiscal,
    ]
    return np.select(condicoes, CATEGORIAS, default=SEM_CLASSIFICACAO)


def prepararLotesClassificados(dfLotes: pd.DataFrame) -> pd.DataFrame:
    """Descarta imóveis sem área ou módulo fiscal e calcula a coluna ``categoria``."""
    if dfLotes.empty:
        return dfLotes.assign(categoria=pd.Series(dtype=object))
    dfClassificado = dfLotes.dropna(subset=["modulo_fiscal", "area"]).copy()
    dfClassificado["categoria"] = classificarPorModuloFiscal(
        dfClassificado["area"], dfClassificado["modulo_fiscal"]
    )
    return dfClassificado


def contarPorCategoria(dfClassificado: pd.DataFrame) -> tuple[dict, int]:
    """Quantidade de imóveis por categoria, na ordem de ``CATEGORIAS``, e o total."""
    contagem = dfClassificado["categoria"].value_counts()
    resultado = {cat: int(contagem[cat]) for cat in CATEGORIAS if contagem.get(cat, 0) > 0}
    return resultado, int(sum(resultado.values()))


def somarAreaPorCategoria(dfClassificado: pd.DataFrame) -> dict:
    """Área total, em hectares, por categoria, na ordem de ``CATEGORIAS``."""
    soma = dfClassificado.groupby("categoria")["area"].sum()
    return {cat: float(soma[cat]) for cat in CATEGORIAS if soma.get(cat, 0) > 0}
