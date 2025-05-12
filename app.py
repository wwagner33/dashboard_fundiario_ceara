# app.py

import streamlit as st
import pandas as pd
import numpy as np
from streamlit_folium import st_folium

from modules import (
    load_data,
    validate_data,
    filtrar_dados,
    classificar_propriedades,
    plot_barras,
    plot_pizza,
    compute_stats_df,
    load_municipios,
    preparar_dados as preparar_dados_ctx,
    criar_choropleth_contextual,
    preprocessar_tudo,
    criar_mapa_com_camadas
)

# ---------------------------------------------------
# 1) set_page_config deve ser o primeiro comando do Streamlit
# ---------------------------------------------------
st.set_page_config(
    page_title="ccTerra::Concentração Fundiária",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------
# 2) Injeta CSS customizado
# ---------------------------------------------------
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ---------------------------------------------------
# 3) Título da aplicação
# ---------------------------------------------------
st.title("ccTerra::Concentração Fundiária")
st.sidebar.markdown("login?")
st.sidebar.markdown("Tem como limitar o tamanho dos gráficos")
st.markdown("<h1 class='custom-header'>Cientista Chefe Terra</h1>", unsafe_allow_html=True)


# ---------------------------------------------------
# 4) Carrega e valida dados
# ---------------------------------------------------
DATA_FOLDER = "data/"
df_raw = load_data(DATA_FOLDER)
df_all, df_class, df_inter, df_ctx, counts = validate_data(df_raw)

# ---------------------------------------------------
# 5) Resumo de Dados usando counts diretamente
# ---------------------------------------------------
st.sidebar.subheader("Resumo de Dados")
descricao_map = {
    'total_carregados': "Total carregados",
    'validos_classificacao': "Válidos classificação",
    'validos_mapa_interativo': "Válidos mapa interativo",
    'validos_mapa_contextual': "Válidos mapa contextual",
    'descartados': "Descartados"
}
resumo = (
    pd.DataFrame.from_dict(counts, orient='index', columns=['Quantidade'])
      .rename_axis('chave')
      .reset_index()
      .assign(Descrição=lambda df: df['chave'].map(descricao_map))
      [['Descrição', 'Quantidade']]
)
st.sidebar.table(resumo)

# ---------------------------------------------------
# 6) Navegação
# ---------------------------------------------------
page = st.sidebar.selectbox(
    "Navegação", ["Gráficos", "Mapa Contextual", "Mapa Interativo"]
)

st.logo("./assets/CC_Terra.png", size="large")

# ---------------------------------------------------
# 7) Lógica de cada aba
# ---------------------------------------------------
if page == "Gráficos":
    opcao = st.sidebar.selectbox(
        "Mostrar por", ["Todo o Estado", "Municípios", "Regiões Administrativas"]
    )
    entidade = None
    if opcao != "Todo o Estado":
        col = "nome_municipio" if opcao == "Municípios" else "regiao_administrativa" 
        entidade = st.sidebar.selectbox(
            f"Selecionar {opcao}",
            sorted(df_class[col].dropna().unique())
        )

    tipo_grafico = st.sidebar.radio("Tipo de gráfico", ["Barras", "Pizza"])

    df_filtrado = filtrar_dados(df_class, opcao, entidade)
    resultados, total = classificar_propriedades(df_filtrado)

    if resultados:
        st.subheader(f"Classificação de Propriedades ({opcao})")
        st.html('<sapn>Dados atualizadoe em xx/xx/2025</span>')
        df_tab = pd.DataFrame(
            list(resultados.items()), columns=["Categoria", "Quantidade"]
        )
        df_tab.loc[len(df_tab)] = ["Total", total]
        st.table(df_tab)

        col1, col2 = st.columns([3, 1])
        data = np.random.randn(10, 1)

        if tipo_grafico == "Barras":
            fig = plot_barras(resultados, f"Propriedades - {opcao}", f"Total: {total}")
            col1.pyplot(fig)
        else:
            fig = plot_pizza(resultados, f"Propriedades - {opcao}", f"Total: {total}")
            col1.pyplot(fig)

        col2.subheader("Estatísticas Adicionais")
        col2.table(compute_stats_df(df_class))

        tab1, tab2, tab3 = st.tabs(["📈 Gráfico", "🗃 Dados", "📈 Circulo"])
        data = np.random.randn(10, 1)

        # tab1.line_chart(data)
        tab1.pyplot(fig) # // colocar as estatisticass adicionais do lado do grafico de pizza

        tab2.subheader("Estatísticas Adicionais")
        # tab2.write(data)
        tab2.table(compute_stats_df(df_class))

        fig = plot_pizza(resultados, f"Propriedades - {opcao}", f"Total: {total}")
        tab3.pyplot(fig)





    else:
        st.warning("Nenhum dado disponível para o filtro selecionado.")

elif page == "Mapa Contextual":
    muni_gdf = load_municipios(DATA_FOLDER)
    gdf_ctx = preparar_dados_ctx(df_ctx, muni_gdf)
    mapa = criar_choropleth_contextual(gdf_ctx)
    st_folium(mapa, width=800, height=600)

else:  # Mapa Interativo
    gdf_inter = preprocessar_tudo(df_inter)
    sel_regiao = st.sidebar.selectbox(
        "Região Administrativa",
        sorted(gdf_inter['regiao_administrativa'].unique())
    )
    mapa = criar_mapa_com_camadas(gdf_inter, sel_regiao)

    st_folium(mapa, width=800, height=600)
