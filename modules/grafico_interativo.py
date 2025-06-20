# modules/grafico_interativo.py

"""
Funções para gerar os gráficos de classificação:
- filtrar_dados(df_class, scope, entidade)
- classificar_propriedades(df_filtrado)
- plot_barras(resultados, titulo, subtitulo)
- plot_pizza(resultados, titulo, subtitulo)
- compute_stats_df(df_class)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from public.cores import CORES as cores

# Add this near the top of the code (with other constants)


CORES = cores
CORES["Sem Registro"] = "#9fa2a5"



def filtrar_dados(df: pd.DataFrame, scope: str, entidade: str = None) -> pd.DataFrame:
    if scope == "Todo o Estado":
        return df
    elif scope == "Municípios":
        return df[df["nome_municipio"] == entidade]
    elif scope == "Regiões Administrativas":
        return df[df["regiao_administrativa"] == entidade]
    else:
        raise ValueError(f"Escopo desconhecido: {scope}")


def classificar_propriedades(df: pd.DataFrame):
    mf = df["modulo_fiscal"]
    area = df["area"]
    categorias = np.where(
        area < mf,
        "Pequena Propriedade < 1 MF",
        np.where(
            area <= 4 * mf,
            "Pequena Propriedade",
            np.where(area <= 15 * mf, "Média Propriedade", "Grande Propriedade"),
        ),
    )
    counts = pd.Series(categorias).value_counts().to_dict()
    total = int(sum(counts.values()))
    return counts, total


# Modify the plot_barras function:
def plot_barras(resultados, titulo, subtitulo) -> plt.Figure:
    """
    Plota gráfico de barras com os valores e anota os totais acima de cada barra.
    """
    # Map category names to colors
    color_map = {
        "Pequena Propriedade < 1 MF": CORES["Pequena Propriedade < 1 MF"],
        "Pequena Propriedade": CORES["Pequena Propriedade"],
        "Média Propriedade": CORES["Média Propriedade"],
        "Grande Propriedade": CORES["Grande Propriedade"],
    }
    fig, ax = plt.subplots(figsize=(10, 10))

    # Get colors in correct order
    colors = [color_map[cat] for cat in resultados.keys()]

    bars = ax.bar(
        resultados.keys(),
        resultados.values(),
        color=colors,
        edgecolor="black",
        alpha=0.85,
    )
    ax.set_title(f"{titulo}\n{subtitulo}", fontsize=16)
    plt.xlabel("Categoria", fontsize=14)
    plt.ylabel("Número de Propriedades", fontsize=14)
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.xticks(rotation=45, fontsize=12)

    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"{int(height)}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
        )
    plt.tight_layout()
    return fig


# Modify the plot_pizza function:
def plot_pizza(resultados, titulo, subtitulo) -> plt.Figure:
    """
    Plota gráfico de pizza com percentuais e legenda.
    Esse gráfico é tão gostoso quanto uma fatia de pizza (sem exageros, ok?).
    """
    # Map category names to colors
    color_map = {
        "Pequena Propriedade < 1 MF": CORES["Pequena Propriedade < 1 MF"],
        "Pequena Propriedade": CORES["Pequena Propriedade"],
        "Média Propriedade": CORES["Média Propriedade"],
        "Grande Propriedade": CORES["Grande Propriedade"],
    }
    fig, ax = plt.subplots(figsize=(10, 10))

    # Get colors in correct order
    colors = [color_map[cat] for cat in resultados.keys()]

    # plt.figure(figsize=(10, 10))
    wedges, texts, autotexts = ax.pie(
        list(resultados.values()),
        labels=None,
        autopct="%1.1f%%",
        startangle=90,
        colors=colors,
        pctdistance=0.8,
    )
    ax.set_title(f"{titulo}\n{subtitulo}", fontsize=16)
    ax.axis("equal")
    ax.legend(
        wedges,
        resultados.keys(),
        title="Tipos de Propriedade",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
    )
    plt.tight_layout()
    return fig


def compute_stats_df(df: pd.DataFrame) -> pd.DataFrame:
    stats = df["area"].describe()
    stats = stats.rename(
        {
            "count": "Contagem",
            "mean": "Média",
            "std": "Desvio Padrão",
            "min": "Mínimo",
            "25%": "1º Quartil",
            "50%": "Mediana",
            "75%": "3º Quartil",
            "max": "Máximo",
        }
    )
    return (
        stats.to_frame(name="Área (ha)")
        .reset_index()
        .rename(columns={"index": "Estatística"})
    )
