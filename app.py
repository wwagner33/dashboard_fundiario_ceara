# app.py


import streamlit as st
import pandas as pd
from streamlit_folium import st_folium

from modules import (
    load_csv_data as load_data,
    load_municipios,
    validate_data,
    filtrar_dados,
    classificar_propriedades,
    plot_barras,
    plot_pizza,
    compute_stats_df,
    load_municipios,
    preparar_dados as preparar_dados_ctx,
    criar_mapa_contextual,
    preprocessar_tudo,
    criar_mapa_com_camadas,
)

# -----------------------------
# 🔒 Aplicação de Cache
# -----------------------------

# Cacheia a leitura de CSVs e DataFrames pesados (expira em 1h)
load_data = st.cache_data(ttl=3600)(
    load_data
)  # :contentReference[oaicite:2]{index=2} :contentReference[oaicite:3]{index=3}

# Cacheia validações e splits de dados (poupando re-execuções)
validate_data = st.cache_data()(validate_data)  # :contentReference[oaicite:4]{index=4}

# Cacheia filtros, classificações e estatísticas
filtrar_dados = st.cache_data()(filtrar_dados)
classificar_propriedades = st.cache_data()(classificar_propriedades)
compute_stats_df = st.cache_data()(
    compute_stats_df
)  # :contentReference[oaicite:5]{index=5}

# Cacheia GeoDataFrame de municípios e preparação de contexto
load_municipios = st.cache_data()(load_municipios)
preparar_dados_ctx = st.cache_data()(preparar_dados_ctx)
preprocessar_tudo = st.cache_data()(
    preprocessar_tudo
)  # :contentReference[oaicite:6]{index=6}

# -----------------------------
# 🚀 App Streamlit
# -----------------------------

st.set_page_config(
    page_title="ccTerra::Análise da Concentração Fundiária do Ceará",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("ccTerra::Concentração Fundiária")

# Carrega e valida dados
DATA_FOLDER = "data/"
df_raw = load_data(DATA_FOLDER)
df_all, df_class, df_inter, df_ctx, counts = validate_data(df_raw)

# 2) Resumo de Dados na sidebar # Usado para debug
# descricao_map = { # Usado para debug
#     "total_carregados": "Total carregados",
#     "validos_classificacao": "Válidos classificação",
#     "validos_mapa_interativo": "Válidos mapa interativo",
#     "validos_mapa_contextual": "Válidos mapa contextual",
#     "descartados": "Descartados",
# }
# resumo = (
#     pd.DataFrame.from_dict(counts, orient="index", columns=["Quantidade"])
#     .rename_axis("chave")
#     .reset_index()
#     .assign(Descrição=lambda df: df["chave"].map(descricao_map))[
#         ["Descrição", "Quantidade"]
#     ]
# ) # Usado para debug
# st.sidebar.subheader("Resumo de Dados") # Usado para debug
# st.sidebar.table(resumo) # Usado para debug

# Navegação
page = st.sidebar.selectbox(
    "Navegação", ["Gráficos", "Mapa Contextual", "Mapa Interativo"]
)

# Lógica por aba
if page == "Gráficos":
    opcao = st.sidebar.selectbox(
        "Mostrar por", ["Todo o Estado", "Municípios", "Regiões Administrativas"]
    )
    entidade = None
    if opcao != "Todo o Estado":
        col = "nome_municipio" if opcao == "Municípios" else "regiao_administrativa"
        entidade = st.sidebar.selectbox(
            f"Selecionar {opcao}", sorted(df_class[col].dropna().unique())
        )
    tipo_grafico = st.sidebar.radio("Tipo de gráfico", ["Barras", "Pizza"])

    df_filtrado = filtrar_dados(df_class, opcao, entidade)
    resultados, total = classificar_propriedades(df_filtrado)

    if resultados:
        st.subheader(f"Classificação de Propriedades ({opcao})")
        df_tab = pd.DataFrame(
            list(resultados.items()), columns=["Categoria", "Quantidade"]
        )
        df_tab.loc[len(df_tab)] = ["Total", total]
        st.table(df_tab)

        if tipo_grafico == "Barras":
            fig = plot_barras(resultados, f"Propriedades - {opcao}", f"Total: {total}")
        else:
            fig = plot_pizza(resultados, f"Propriedades - {opcao}", f"Total: {total}")
        st.pyplot(fig)

        st.subheader("Estatísticas Adicionais")
        st.table(compute_stats_df(df_class))
    else:
        st.warning("Nenhum dado disponível para o filtro selecionado.")

elif page == "Mapa Contextual":
    muni_gdf = load_municipios(DATA_FOLDER)
    gdf_ctx = preparar_dados_ctx(df_ctx, muni_gdf)
    mapa = criar_mapa_contextual(gdf_ctx)
    st_folium(mapa, width=800, height=600)

else:  # Mapa Interativo
    #gdf_inter = preprocessar_tudo(df_inter)
    sel_regiao = st.sidebar.selectbox(
        "Região Administrativa", sorted(df_inter["regiao_administrativa"].unique())
    )
    mapa = criar_mapa_com_camadas(df_inter, sel_regiao)
    st_folium(mapa, width=800, height=600)