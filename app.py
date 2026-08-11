# app.py
import streamlit as st
import pandas as pd
import numpy as np
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
    render_terra_ai,
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

# ---------------------------------------------------
# 0) Definição de funções de visualizações
# --------------------------------------------------- 
def graficos_e_quadros():
    col1, col2 = st.columns([1, 1]) 
    tab1, tab2 = col1.tabs(["📈 Barra", "📈 Pizza"])
    co2_1, co2_2 = col2.columns([1, 1]) 
    opcao = co2_1.selectbox(
        "Mostrar por", ["Todo o Estado", "Municípios", "Regiões Administrativas"]
    )
    entidade = None
    if opcao != "Todo o Estado":
        col = "nome_municipio" if opcao == "Municípios" else "regiao_administrativa" 
        entidade = co2_2.selectbox(
            f"Selecionar {opcao}",
            sorted(df_class[col].dropna().unique())
        )

    df_filtrado = filtrar_dados(df_class, opcao, entidade)
    resultados, total = classificar_propriedades(df_filtrado)

    def preencher_tabs():
        fig_barra = plot_barras(resultados, f"Propriedades - {opcao} - {entidade}", f"Total: {total}")
        fig_pizza = plot_pizza(resultados, f"Propriedades - {opcao} - {entidade}", f"Total: {total}")
            
        tab1.pyplot(fig_barra)
        tab2.pyplot(fig_pizza)

        col2.subheader(f"Classificação de Propriedades ({opcao} - {entidade})")
        col2.table(df_tab)

        col2.subheader("Estatísticas Adicionais")
        col2.table(compute_stats_df(df_class))
        fig = plot_pizza(resultados, f"Propriedades - {opcao}", f"Total: {total}")
    
    if resultados:
        st.html('<sapn>Dados atualizadoe em xx/xx/2025</span>')
        df_tab = pd.DataFrame(
            list(resultados.items()), columns=["Categoria", "Quantidade"]
        )
        df_tab.loc[len(df_tab)] = ["Total", total]

        # Tabs
        preencher_tabs()
        
    else:
        st.warning("Nenhum dado disponível para o filtro selecionado.")

def mapa_contextuall():
    muni_gdf = load_municipios(DATA_FOLDER)
    gdf_ctx = preparar_dados_ctx(df_ctx, muni_gdf)
    mapa = criar_mapa_contextual(gdf_ctx)
    st_folium(mapa, width=800, height=600)

def mapa_interativo():
    sel_regiao = st.sidebar.selectbox(
        "Região Administrativa", sorted(df_inter["regiao_administrativa"].unique())
    )
    mapa = criar_mapa_com_camadas(df_inter, sel_regiao)
    st_folium(mapa, width=800, height=600)



# ---------------------------------------------------
# 1) set_page_config deve ser o primeiro comando do Streamlit
# ---------------------------------------------------
st.set_page_config(
    page_title="ccTerra::Análise da Concentração Fundiária do Ceará",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("ccTerra::Classificação de Lotes")
st.markdown("<h1 class='custom-header'>ccTerra::Dashboard Fundiário</h1>", unsafe_allow_html=True)


# Carrega e valida dados
DATA_FOLDER = "data/"
df_raw = load_data(DATA_FOLDER)
df_all, df_class, df_inter, df_ctx, counts = validate_data(df_raw)


# ---------------------------------------------------
# 6) Navegação
# ---------------------------------------------------
page = st.sidebar.selectbox(
    "Navegação", ["Gráficos", "Mapa Contextual", "Mapa Interativo", "Terra-AI"]
)


st.logo("./assets/CC_Terra.png", size="large")

# ---------------------------------------------------
# 7) Lógica de cada aba
# ---------------------------------------------------
if page == "Gráficos":
   graficos_e_quadros()

elif page == "Mapa Contextual":
   mapa_contextuall()

elif page == "Mapa Interativo":
   mapa_interativo()

else:  # Terra-AI
   render_terra_ai()
