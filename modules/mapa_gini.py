# import streamlit as st
# import pandas as pd
# import folium
# import numpy as np
# from folium.features import GeoJsonTooltip
# from shapely.geometry import Polygon, MultiPolygon
# from streamlit_folium import st_folium
# from folium.plugins import MiniMap, Fullscreen
# from modules.mapa_reservatorios import adicionar_camada_municipios, carregar_municipios
# from public.cores import CORES_GINI

# # Cálculo de Gini Fundiário
# def gini(arr):
#     a = np.array(arr, dtype=float)
#     a = a[~np.isnan(a)]  # remove NaNs
#     a = a[a > 0]         # remove zeros e negativos
#     a = np.sort(a)
#     n = a.size
#     if n == 0:
#         return float("nan")
#     total = a.sum()
#     if total == 0:
#         return float("nan")
#     idx = np.arange(1, n + 1)
#     return (2 * (idx * a).sum()) / (n * total) - (n + 1) / n

# # Prepara DataFrames para cálculos
# @st.cache_data
# def processar_dataframes(df_props, out_iqr, out_err):
#     df_with = df_props.copy()
#     df_no = df_props.drop(pd.concat([out_iqr, out_err]).drop_duplicates().index)
#     return df_with, df_no

# def contar_lotes(df_with, df_no):
#     for df in [df_with, df_no]:
#         df["cnt"] = df.groupby("nome_municipio")["area"].transform("count")
#     warning_munis = df_with[df_with["cnt"] < 100]["nome_municipio"].unique().tolist()
#     return df_with, df_no, warning_munis

# # Geração DataFrame de Gini por município
# def calc_gini_df(df):
#     return (
#         df.groupby("nome_municipio")
#           .agg(
#             nome_municipio_original=("nome_municipio_original", "first"),
#             regiao_administrativa=("regiao_administrativa", "first"),
#             cnt=("area", "count"),
#             gini_area=("area", gini),
#           )
#           .reset_index()
#     )

# # Função para gerar gráfico circular do Gini
# def gerar_grafico_circular(valor, tamanho=100):
#     if pd.isna(valor):
#         return "<div>Sem dados</div>"
#     valor_str = f"{valor:.2%}".replace(".", ",")
#     valor_abs = f"{valor:.4f}".replace(".", ",")
#     html = f"""
#     <style>
#     .grafico {{
#         --porcentagem: {valor:.2f};
#         --tamanho: {tamanho}px;
#         width: var(--tamanho);
#         height: var(--tamanho);
#         border-radius: 50%;
#         background: conic-gradient(
#             {CORES_GINI[2]} 0%,
#             #f5e1df calc(var(--porcentagem) * 100%),
#             #fcf1f0 0%
#         );
#         display: grid; place-items: center; margin: 10px auto;
#     }}
#     .grafico::before {{
#         content: "{valor_str}";
#         display: grid; place-items: center;
#         width: 70%; height: 70%; background: white; border-radius: 50%;
#         color: #0c0906; font-size: {tamanho * 0.15}px;
#     }}
#     </style>
#     <div class="grafico" data-value="{valor:.0%}"></div>
#     <p style='text-align:center;color:black; padding-bottom:0px;'>Valor absoluto: {valor_abs}</p>
#     """
#     return html

# # Estilo de polígonos (sem cache)
# def style_fn(f):
#     p = f["properties"]
#     cnt = p.get("cnt")
#     if cnt and cnt < 100:
#         return {"fillColor": CORES_GINI[0], "color": "black", "weight": 0.5, "fillOpacity": 0.8}
#     g = p.get("gini_area")
#     if pd.isna(g):
#         return {"fillColor": "#D3D3D3", "color": "black", "weight": 0.5, "fillOpacity": 0.8}
#     if g <= 0.700:
#         c = CORES_GINI[1]
#     elif g <= 0.800:
#         c = CORES_GINI[2]
#     elif g <= 0.850:
#         c = CORES_GINI[3]
#     elif g <= 0.900:
#         c = CORES_GINI[4]
#     else:
#         c = CORES_GINI[5]
#     return {"fillColor": c, "color": "black", "weight": 0.5, "fillOpacity": 0.8}

# # Renderização de mapas com clique habilitado
# def render_map(tab, geo_df):
#     with tab:
#         m = folium.Map(location=[-5.2, -39.5], zoom_start=8, tiles="cartodbpositron", control_scale=True,prefer_canvas=True)
#         if "geo_muni" not in st.session_state:
#             st.session_state.geo_muni = carregar_municipios("todos")
#         adicionar_camada_municipios(m, st.session_state.geo_muni)
#         tooltip = GeoJsonTooltip(
#             fields=["nome_municipio_original", "gini_area", "cnt"],
#             aliases=["Município: ", "Índice de Gini: ", "Imóveis: "],
#             localize=True, sticky=True,
#         )
#         folium.GeoJson(geo_df, style_function=style_fn, tooltip=tooltip, name="gini_map").add_to(m)
#         for _, row in geo_df.iterrows():
#             geom = row.geometry
#             if isinstance(geom, (Polygon, MultiPolygon)):
#                 c = geom.centroid
#                 folium.map.Marker(
#                     [c.y, c.x],
#                     icon=folium.DivIcon(html=f"<div style='font-size:6pt;font-weight:bold;color:black;text-shadow:0 0 4px white;'>{row['nome_municipio']}</div>"),
#                 ).add_to(m)
#         legend_html = f"""
#             <div style='position:fixed;top:10px;right:10px;background:white;padding:10px;border:1px solid grey;font-size:14px;z-index:9999;'>
#             <b>Intervalos de Gini</b><br>
#             <i style='background:{CORES_GINI[0]};width:12px;height:12px;float:left;margin-right:4px'></i> <100 imóveis<br>
#             <i style='background:{CORES_GINI[1]};width:12px;height:12px;float:left;margin-right:4px'></i>≤0.700<br>
#             <i style='background:{CORES_GINI[2]};width:12px;height:12px;float:left;margin-right:4px'></i>0.701–0.800<br>
#             <i style='background:{CORES_GINI[3]};width:12px;height:12px;float:left;margin-right:4px'></i>0.801–0.850<br>
#             <i style='background:{CORES_GINI[4]};width:12px;height:12px;float:left;margin-right:4px'></i>0.851–0.900<br>
#             <i style='background:{CORES_GINI[5]};width:12px;height:12px;float:left;margin-right:4px'></i>>0.900<br>
#             <i style='background:#D3D3D3;width:12px;height:12px;float:left;margin-right:4px'></i>Sem dados
#             </div>"""
#         m.get_root().html.add_child(folium.Element(legend_html))
        
#         MiniMap(toggle_display=True).add_to(m)
#         Fullscreen().add_to(m)
#         return st_folium(
#             m, 
#             width=1024, 
#             height=720, 
#             returned_objects=["last_object_clicked_tooltip"], 
#             use_container_width=True
#             )

# def render_view_gini_map(df_props, municipios, clicou=False):
    
#     # Detecção de outliers
#     areas = df_props["area"]
#     Q1, Q3 = areas.quantile([0.25, 0.75])
#     IQR = Q3 - Q1
#     out_iqr = df_props[(areas < Q1 - 1.5 * IQR) | (areas > Q3 + 1.5 * IQR)]
#     HALF_STATE_HA = 1488860 / 2
#     out_err = df_props[df_props["area"] >= HALF_STATE_HA]
#     df_with, df_no = processar_dataframes(df_props, out_iqr, out_err)
#     df_with, df_no, warning_munis = contar_lotes(df_with, df_no)

#     gini_with = calc_gini_df(df_with)
#     gini_with_filt = gini_with[gini_with["cnt"] >= 1]
#     state_gini = gini(df_with["area"].values)
#     geo_with = municipios.merge(gini_with, on="nome_municipio", how="left")

#     col1, col2 = st.columns([7, 3])
#     map_data = render_map(col1, geo_with)
#     clicou = False
    
#     # Sofrimento e dor para descobrir este parâmetro "last_object_clicked_tooltip" (se usar o "last_object_clicked", ele retorna somente Lat e Lon)
#     # e mais sofrimento para descobrir que ele retorna 
#     # uma string grande que teria que ser "fatiada"
#     # Deixo aqui este registro para que outros não sofram tanto quanto eu sofri
#     # Se o mapa foi clicado e contém dados, processa o clique
#     # e as informações do tooltip são apssadas como string com apenas um "\n" entre elas
#     # no formato:
#     """
#     Aracoiaba
    
#     Índice Gini: 
    
#     0.7890
    
#     Quantidade de imóveis: 
    
#     1500
#     """
    
    
#     clicked_data = map_data.get("last_object_clicked_tooltip") if map_data else None
#     # Limpa e extrai os dados da string recebida pelo método get("last_object_clicked_tooltip"), depois desenha o gráfico circular
#     if 'gini_estadual_clicado' not in st.session_state:
#         st.session_state.gini_estadual_clicado = clicou

#     with col2:
#         st.html("""
#                 <p class="paragrafo-com-icone" style="font-size: 14px !important;">
#                     <span class="icone-svg"></span> 
#                     Este mapa apresenta o Índice de Gini da distribuição fundiária por município no Ceará,
#                     permitindo identificar o grau de concentração de terras.  
#                     Inclui também um indicador geral do estado. </br>
#                     As áreas em amarelo são regiões onde o número de imóveis é inferior a 100, portanto,
#                     abaixo do número mínimo de imóveis necessário para cálculo correto do Gini Fundiário. </br>
#                     Os municípios em branco, no mapa, são correspondentes às áreas áreas rurais ainda não regularizadas.
#                 </p>
#                 """)
#         st.markdown("### Índice de Gini")
#         st.html("""<span style='color: #000000 !important'>Do Estado do Ceará </span>
#                 """)
#         ## Exibe gráfico circular do Gini de um municipio específico   
#         if clicked_data and not st.session_state.gini_estadual_clicado:
#             ## Remove linhas vazias e espaços extras
#             lines = [line.strip() for line in clicked_data.split("\n") if line.strip()]

#             ## Extrai os valores
#             municipio = lines[1] if len(lines) > 1 else None
#             municipios_unicos = geo_with['nome_municipio_original'].unique().tolist()
#             if municipio in municipios_unicos:
#                 gini_mun_str = lines[3].replace(",", ".")
#                 gini_mun = float(gini_mun_str) if gini_mun_str else None
#                 st.markdown(f"<p style='text-align: center; color:black;'>{municipio}</p>", unsafe_allow_html=True)
#                 if gini_mun is not None:
#                     st.markdown(gerar_grafico_circular(gini_mun, 150), unsafe_allow_html=True)
#                     if st.button("Mostrar Gini Estadual Completo", key="mostrar_gini_estadual_completo", use_container_width=True):
#                         st.session_state.gini_estadual_clicado = True
#                         st.rerun()
#             else:
#                 st.markdown(gerar_grafico_circular(state_gini, 180), unsafe_allow_html=True)
#                 st.session_state.gini_estadual_clicado = False
#         else:
#             st.markdown(gerar_grafico_circular(state_gini, 180), unsafe_allow_html=True)
#             st.session_state.gini_estadual_clicado = False


#         st.html("""
#                 <p class="paragrafo-com-icone" style="font-size: 16px !important;">
#                     <span class="icone-svg"></span> 
#                     As cores indicam faixas de desigualdade, e o usuário pode clicar 
#                     sobre um município para visualizar seu valor específico em destaque,
#                     além de consultar rankings por região administrativa.  
#                 </p>
#                 """)

#         st.subheader("Gini por Região Administrativa")
#         regioes = gini_with_filt["regiao_administrativa"].unique().tolist()
#         regiao_selecionada = st.selectbox("Filtrar por Região:", options=["[TODAS]"] + sorted(regioes), index=0)
#         if regiao_selecionada != "[TODAS]":
#             df_tabela = gini_with_filt[gini_with_filt["regiao_administrativa"] == regiao_selecionada]
#         else:
#             df_tabela = gini_with_filt
#         st.dataframe(
#             df_tabela[["regiao_administrativa", "nome_municipio_original", "cnt", "gini_area"]]
#             .rename(columns={
#                 "regiao_administrativa": "Região",
#                 "nome_municipio_original": "Município",
#                 "gini_area": "Gini",
#                 "cnt": "Qtd. Lotes",
#             })
#             .sort_values("Município", ascending=True),
#             use_container_width=True, hide_index=True, height=600
#         )    
#     return clicou

import streamlit as st
import pandas as pd
import folium
import numpy as np
from folium.features import GeoJsonTooltip
from shapely.geometry import Polygon, MultiPolygon
from streamlit_folium import st_folium
from folium.plugins import MiniMap, Fullscreen
from modules.mapa_reservatorios import adicionar_camada_municipios, carregar_municipios
from public.cores import CORES_GINI
import unicodedata

# Função para normalizar strings (remover acentos e converter para minúsculas)
def normalizar_texto(texto):
    if pd.isna(texto):
        return texto
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').lower()

# Cálculo de Gini
def gini(arr):
    """Calcula o Índice de Gini para uma distribuição de valores (áreas de terras).
    Fórmula: (2 * Σ(i * x_i)) / (n * Σx_i) - (n+1)/n
    - Remove valores inválidos (NaNs, negativos)
    - Retorna NaN para amostras vazias ou soma zero"""
    
    a = np.array(arr, dtype=float)
    a = a[~np.isnan(a)]  # remove NaNs
    a = a[a > 0]         # remove zeros e negativos
    a = np.sort(a)
    n = a.size
    if n == 0:
        return float("nan")
    total = a.sum()
    if total == 0:
        return float("nan")
    idx = np.arange(1, n + 1)
    return (2 * (idx * a).sum()) / (n * total) - (n + 1) / n

# Prepara DataFrames para cálculos com agrupamento por proprietário
@st.cache_data
def processar_dataframes(df_props, out_iqr, out_err):
    """Prepara os dados para cálculo do Gini:
       1. Cria duas versões dos dados: 
          - Com todos os registros (incluindo outliers)
          - Sem outliers estatísticos/cadastrais
       2. Agrupa imóveis por proprietário (soma de áreas por município)
       3. Adiciona contagem de imóveis por município"""
    # Cria cópias dos DataFrames
    df_with = df_props.copy()
    df_no = df_props.drop(pd.concat([out_iqr, out_err]).drop_duplicates().index)
    
    # Normaliza nomes de proprietários
    df_with['nome_proprietario_normalizado'] = df_with['nome_proprietario'].apply(normalizar_texto)
    df_no['nome_proprietario_normalizado'] = df_no['nome_proprietario'].apply(normalizar_texto)
    
    # Calcula contagem de imóveis por município
    contagem_imoveis_with = df_with.groupby('nome_municipio').size().reset_index(name='cnt_imoveis')
    contagem_imoveis_no = df_no.groupby('nome_municipio').size().reset_index(name='cnt_imoveis')
    
    # Agrupa por proprietário e município (soma das áreas)
    df_with_agrupado = df_with.groupby(['nome_municipio', 'nome_proprietario_normalizado']).agg(
        area=('area', 'sum'),
        nome_municipio_original=('nome_municipio_original', 'first'),
        regiao_administrativa=('regiao_administrativa', 'first')
    ).reset_index()
    
    df_no_agrupado = df_no.groupby(['nome_municipio', 'nome_proprietario_normalizado']).agg(
        area=('area', 'sum'),
        nome_municipio_original=('nome_municipio_original', 'first'),
        regiao_administrativa=('regiao_administrativa', 'first')
    ).reset_index()
    
    # Adiciona contagem de imóveis aos DataFrames agrupados
    df_with_agrupado = df_with_agrupado.merge(contagem_imoveis_with, on='nome_municipio', how='left')
    df_no_agrupado = df_no_agrupado.merge(contagem_imoveis_no, on='nome_municipio', how='left')
    
    return df_with_agrupado, df_no_agrupado

def contar_lotes(df_with, df_no):
    # Identifica municípios com menos de 200 imóveis
    warning_munis = df_with[df_with["cnt_imoveis"] < 200]["nome_municipio"].unique().tolist()
    return df_with, df_no, warning_munis

# Geração DataFrame de Gini por município
def calc_gini_df(df):
    return (
        df.groupby("nome_municipio")
          .agg(
            nome_municipio_original=("nome_municipio_original", "first"),
            regiao_administrativa=("regiao_administrativa", "first"),
            cnt_imoveis=("cnt_imoveis", "first"),
            cnt_proprietarios=("nome_proprietario_normalizado", "nunique"),
            gini_area=("area", gini),
          )
          .reset_index()
    )

# Função para gerar gráfico circular do Gini
def gerar_grafico_circular(valor, tamanho=100):
    if pd.isna(valor):
        return "<div>Sem dados</div>"
    valor_str = f"{valor:.2%}".replace(".", ",")
    valor_abs = f"{valor:.4f}".replace(".", ",")
    html = f"""
    <style>
    .grafico {{
        --porcentagem: {valor:.2f};
        --tamanho: {tamanho}px;
        width: var(--tamanho);
        height: var(--tamanho);
        border-radius: 50%;
        background: conic-gradient(
            {CORES_GINI[2]} 0%,
            #f5e1df calc(var(--porcentagem) * 100%),
            #fcf1f0 0%
        );
        display: grid; place-items: center; margin: 10px auto;
    }}
    .grafico::before {{
        content: "{valor_abs}";
        display: grid; place-items: center;
        width: 70%; height: 70%; background: white; border-radius: 50%;
        color: #0c0906; font-size: {tamanho * 0.15}px;
    }}
    </style>
    <div class="grafico" data-value="{valor:.0%}"></div>
    <p style='text-align:center;color:black; padding-bottom:0px; margin-right: auto;'>Percentual:</br> {valor:.2%}     </p>
    """
    return html

# Estilo de polígonos
def style_fn(f):
    p = f["properties"]
    cnt = p.get("cnt_imoveis")
    if cnt and cnt < 200:
        return {"fillColor": CORES_GINI[0], "color": "black", "weight": 0.5, "fillOpacity": 0.8}
    g = p.get("gini_area")
    if pd.isna(g):
        return {"fillColor": "#D3D3D3", "color": "black", "weight": 0.5, "fillOpacity": 0.8}
    if g <= 0.700:
        c = CORES_GINI[1]
    elif g <= 0.800:
        c = CORES_GINI[2]
    elif g <= 0.850:
        c = CORES_GINI[3]
    elif g <= 0.900:
        c = CORES_GINI[4]
    else:
        c = CORES_GINI[5]
    return {"fillColor": c, "color": "black", "weight": 0.5, "fillOpacity": 0.8}

# Renderização de mapas com clique habilitado
def render_map(tab, geo_df):
    with tab:
        m = folium.Map(location=[-5.2, -39.5], zoom_start=8, tiles="cartodbpositron", control_scale=True, prefer_canvas=True)
        if "geo_muni" not in st.session_state:
            st.session_state.geo_muni = carregar_municipios("todos")
        adicionar_camada_municipios(m, st.session_state.geo_muni)
        
        # Tooltip com informações
        tooltip = GeoJsonTooltip(
            fields=["nome_municipio_original", "gini_area", "cnt_imoveis", "cnt_proprietarios"],
            aliases=["Município: ", "Índice de Gini: ", "Imóveis: ", "Proprietários: "],
            localize=True, 
            sticky=True,
        )
        folium.GeoJson(geo_df, style_function=style_fn, tooltip=tooltip, name="gini_map").add_to(m)
        
        for _, row in geo_df.iterrows():
            geom = row.geometry
            if isinstance(geom, (Polygon, MultiPolygon)):
                c = geom.centroid
                folium.map.Marker(
                    [c.y, c.x],
                    icon=folium.DivIcon(html=f"<div style='font-size:6pt;font-weight:bold;color:black;text-shadow:0 0 4px white;'>{row['nome_municipio']}</div>"),
                ).add_to(m)
        
        # Legenda
        legend_html = f"""
            <div style='position:fixed;top:10px;right:10px;background:white;padding:10px;border:1px solid grey;font-size:14px;z-index:9999;'>
            <b>Intervalos de Gini</b><br>
            <i style='background:{CORES_GINI[0]};width:12px;height:12px;float:left;margin-right:4px'></i> &lt;200 imóveis<br>
            <i style='background:{CORES_GINI[1]};width:12px;height:12px;float:left;margin-right:4px'></i>≤0.700<br>
            <i style='background:{CORES_GINI[2]};width:12px;height:12px;float:left;margin-right:4px'></i>0.701–0.800<br>
            <i style='background:{CORES_GINI[3]};width:12px;height:12px;float:left;margin-right:4px'></i>0.801–0.850<br>
            <i style='background:{CORES_GINI[4]};width:12px;height:12px;float:left;margin-right:4px'></i>0.851–0.900<br>
            <i style='background:{CORES_GINI[5]};width:12px;height:12px;float:left;margin-right:4px'></i>&gt;0.900<br>
            <i style='background:#D3D3D3;width:12px;height:12px;float:left;margin-right:4px'></i>Sem dados
            </div>"""
        m.get_root().html.add_child(folium.Element(legend_html))
        
        MiniMap(toggle_display=True).add_to(m)
        Fullscreen().add_to(m)
        return st_folium(
            m, 
            # width=800, 
            height=600, 
            returned_objects=["last_object_clicked_tooltip"], 
            use_container_width=True
        )

def render_view_gini_map(df_props, municipios, clicou=False):
    # Detecção de outliers
    areas = df_props["area"]
    Q1, Q3 = areas.quantile([0.25, 0.75])
    IQR = Q3 - Q1
    out_iqr = df_props[(areas < Q1 - 1.5 * IQR) | (areas > Q3 + 1.5 * IQR)]
    HALF_STATE_HA = 1488860 / 2
    out_err = df_props[df_props["area"] >= HALF_STATE_HA]
    
    # Processa DataFrames com agrupamento por proprietário
    df_with, df_no = processar_dataframes(df_props, out_iqr, out_err)
    df_with, df_no, warning_munis = contar_lotes(df_with, df_no)

    # Calcula Gini por município
    gini_with = calc_gini_df(df_with)
    
    # Calcula Gini estadual: agrupar todos os proprietários do estado (somar áreas por proprietário) e calcular Gini
    proprietarios_estado = df_with.groupby('nome_proprietario_normalizado')['area'].sum()
    state_gini = gini(proprietarios_estado.values)
    
    # Combina com dados geográficos
    geo_with = municipios.merge(gini_with, on="nome_municipio", how="left")

    col1, col2 = st.columns([10, 3])
    map_data = render_map(col1, geo_with)
    clicou = False
    
    # Processamento do clique
    clicked_data = map_data.get("last_object_clicked_tooltip") if map_data else None
    if 'gini_estadual_clicado' not in st.session_state:
        st.session_state.gini_estadual_clicado = clicou

    with col2:
        st.html("""
                <p class="paragrafo-com-icone" style="font-size: 14px !important;">
                    <span class="icone-svg"></span> 
                    Este mapa apresenta o Índice de Gini da distribuição fundiária por município no Ceará,
                    permitindo identificar o grau de concentração de terras.  
                    Inclui também um indicador geral do estado. </br>
                    As áreas em amarelo são regiões onde o número de imóveis é inferior a 200, portanto,
                    abaixo do número mínimo de imóveis necessário para cálculo correto do Gini Fundiário. </br>
                    Os municípios em branco, no mapa, são correspondentes às áreas áreas rurais ainda não regularizadas.
                </p>
                """)
        st.markdown("### Índice de Gini")
        st.html("""<span style='color: #000000 !important'>Do Estado do Ceará </span>
                """)
        
        ## Exibe gráfico circular do Gini
        if clicked_data and not st.session_state.gini_estadual_clicado:
            lines = [line.strip() for line in clicked_data.split("\n") if line.strip()]
            municipio = lines[1] if len(lines) > 1 else None
            municipios_unicos = geo_with['nome_municipio_original'].unique().tolist()
            
            if municipio in municipios_unicos:
                gini_mun_str = lines[3].replace(",", ".")
                gini_mun = float(gini_mun_str) if gini_mun_str else None
                st.markdown(f"<p style='text-align: center; color:black;'>{municipio}</p>", unsafe_allow_html=True)
                
                if gini_mun is not None:
                    st.markdown(gerar_grafico_circular(gini_mun, 150), unsafe_allow_html=True)
                    if st.button("Mostrar Gini Estadual Completo", key="mostrar_gini_estadual_completo", use_container_width=True):
                        st.session_state.gini_estadual_clicado = True
                        st.rerun()
            else:
                st.markdown(gerar_grafico_circular(state_gini, 180), unsafe_allow_html=True)
                st.session_state.gini_estadual_clicado = False
        else:
            st.markdown(gerar_grafico_circular(state_gini, 180), unsafe_allow_html=True)
            st.session_state.gini_estadual_clicado = False

        st.html("""
                <p class="paragrafo-com-icone" style="font-size: 16px !important;">
                    <span class="icone-svg"></span> 
                    As cores indicam faixas de desigualdade, e o usuário pode clicar 
                    sobre um município para visualizar seu valor específico em destaque,
                    além de consultar rankings por região administrativa.  
                </p>
                """)

        st.subheader("Gini por Região Administrativa")
        regioes = gini_with["regiao_administrativa"].unique().tolist()
        regiao_selecionada = st.selectbox("Filtrar por Região:", options=["[TODAS]"] + sorted(regioes), index=0)
        
        if regiao_selecionada != "[TODAS]":
            df_tabela = gini_with[gini_with["regiao_administrativa"] == regiao_selecionada]
        else:
            df_tabela = gini_with
        
        # Tabela com informações
        st.dataframe(
            df_tabela[["regiao_administrativa", "nome_municipio_original", "cnt_imoveis", "cnt_proprietarios", "gini_area"]]
            .rename(columns={
                "regiao_administrativa": "Região",
                "nome_municipio_original": "Município",
                "gini_area": "Gini",
                "cnt_imoveis": "Imóveis",
                "cnt_proprietarios": "Proprietários",
            })
            .sort_values("Município", ascending=True),
            use_container_width=True, 
            hide_index=True, 
            height=600
        )    
    return clicou
