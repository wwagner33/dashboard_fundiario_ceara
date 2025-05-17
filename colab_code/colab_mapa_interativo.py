import geopandas as gpd
import pandas as pd
import unicodedata
import json
import geopandas as gpd
import pandas as pd
import folium
import numpy as np
from shapely import wkt
import ipywidgets as widgets
from google.colab import output
from IPython.display import display, clear_output

import os



def get_latest_dataset():
    # Caminho da pasta onde estão os datasets
    pasta_datasets = 'data/'

    # Padrão de nome dos arquivos
    prefixo = 'dataset-malha-fundiaria-idace_preprocessado-'
    sufixo = '.csv'

    # Listar todos os arquivos na pasta
    arquivos = os.listdir(pasta_datasets)

    # Filtrar só os arquivos que seguem o padrão
    arquivos_dataset = [f for f in arquivos if f.startswith(prefixo) and f.endswith(sufixo)]

    if not arquivos_dataset:
        raise FileNotFoundError("Nenhum arquivo de dataset encontrado no diretório especificado.")
    # Ordenar os arquivos com base no timestamp no nome (mais novo por último)
    arquivos_dataset.sort()

    # Pegar o mais novo
    arquivo_mais_recente = arquivos_dataset[-1]

    # Retornar o caminho completo para o arquivo
    return os.path.join(pasta_datasets, arquivo_mais_recente)


def normalizar_nome(nome):
    """
    Remove acentos, converte para minúsculas e substitui espaços por "_".
    """
    if not isinstance(nome, str):
        return nome
    nome_sem_acentos = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    return nome_sem_acentos.lower().replace(" ", "_")

def carregar_dados():
    """
    Carrega os dados dos municípios (GeoJSON) e das propriedades (CSV).
    Normaliza os nomes dos municípios e faz o merge dos datasets.
    Retorna (data, municipios_ce).
    """
    # Carga do dataset mais atual
    caminho_dataset = get_latest_dataset()

    try:
        municipios_ce = gpd.read_file('data/geojson-municipios_ceara-normalizado.geojson')
        print("GeoJSON dos municípios carregado com sucesso.")
    except Exception as e:
        print(f"Erro ao carregar o GeoJSON dos municípios: {e}")
        return None, None

    if 'properties' in municipios_ce.columns:
        props = pd.json_normalize(municipios_ce['properties'])
        municipios_ce = municipios_ce.drop(columns=['properties']).join(props)
        print("Propriedades extraídas e unidas ao DataFrame dos municípios.")

    try:
        data = pd.read_csv(caminho_dataset, low_memory=False)
        print("Dataset das propriedades carregado com sucesso.")
    except Exception as e:
        print(f"Erro ao carregar o dataset das propriedades: {e}")
        return None#, None, None
    # Normaliza os nomes
    data['nome_municipio'] = data['nome_municipio'].apply(normalizar_nome)
    # municipios_ce['NM_MUN'] = municipios_ce['NM_MUN'].apply(normalizar_nome)
    print("Nomes dos municípios normalizados com sucesso.")

    municipios_ce.rename(columns={'NM_MUN': 'nome_municipio'}, inplace=True)
    print("Coluna 'NM_MUN' renomeada para 'nome_municipio'.")

    municipios_unicos_data = set(data['nome_municipio'].unique())
    municipios_unicos_ce = set(municipios_ce['nome_municipio'].unique())
    municipios_faltantes = municipios_unicos_data - municipios_unicos_ce
    if municipios_faltantes:
        print("Atenção: Alguns municípios do dataset não foram encontrados no GeoJSON:")
        print(municipios_faltantes)
    else:
        print("Todos os municípios do dataset foram encontrados no GeoJSON.")
    return data, municipios_ce

# # Carrega os dados
try:
  data,municipios_ce = carregar_dados()
  if data is None:
    print("Dados vazios.")
except Exception as e:
    print(f"Erro ao carregar os dados. \n\n Descrição do erro: \n{e}")
    data = None

# ————————————————————————————————————————————————————————————————————
# Configuração do ambiente
# Ativa widgets no Colab
output.enable_custom_widget_manager()

# ————————————————————————————————————————————————————————————————————
# Configuração de cores por categoria
CORES = {
    "Minifúndio": "#9b19f5",
    "Pequena Propriedade": "#0040bf",
    "Média Propriedade": "#e6d800",
    "Grande Propriedade": "#d97f00",
    "Sem Classificação": "#808080"
}

# # ————————————————————————————————————————————————————————————————————
def carregar_dados_por_regiao(data: pd.DataFrame, regiao: str) -> gpd.GeoDataFrame:
    """Filtra e prepara os dados para a região especificada."""
    df = data[
        (data['regiao_administrativa'] == regiao) &
        data['geom'].notna() &
        data['geom'].apply(lambda x: isinstance(x, str))
    ].copy()
    if df.empty:
        raise ValueError(f"Nenhum dado válido encontrado para: {regiao}")
    return df
# ————————————————————————————————————————————————————————————————————
def preprocessar_tudo(df_raw: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    1) Filtra os dados válidos
    2) Converte WKT para Shapely
    3) Converte para GeoDataFrame
    4) Classifica todas as propriedades
    5) Retorna um GeoDataFrame COMPLETO pronto pra filtrar por região.
    """
    # # só pega linhas com geometria WKT válida
    df = df_raw[df_raw['geom'].notna() & df_raw['geom'].apply(lambda x: isinstance(x, str))].copy()
    
    # converte string WKT em shapely
    def to_geom(w):
        try:
            return wkt.loads(w)
        except:
            return None
    
    df['geometry'] = df['geom'].map(to_geom)
    df = df[df['geometry'].notna()]
    
    # monta GeoDataFrame e projeta
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:31984')
    gdf = gdf.to_crs(epsg=4326)
    
    # Classificação
    conds = [
        (gdf['area'] > 0) & (gdf['area'] < gdf['modulo_fiscal']),
        (gdf['area'] >= gdf['modulo_fiscal']) & (gdf['area'] <= 4 * gdf['modulo_fiscal']),
        (gdf['area'] > 4 * gdf['modulo_fiscal']) & (gdf['area'] <= 15 * gdf['modulo_fiscal']),
        (gdf['area'] > 15 * gdf['modulo_fiscal'])
    ]
    cats = list(CORES.keys())[:-1]
    gdf['categoria'] = np.select(conds, cats, default="Sem Classificação")
    
    return gdf


def criar_mapa_com_camadas(gdf: gpd.GeoDataFrame, regiao: str) -> folium.Map:
    # 1. Centrar o mapa como antes...
    gdf_proj = gdf.to_crs(epsg=31983)
    centro_proj = gdf_proj.geometry.centroid.union_all().centroid
    centro_wgs84 = (
        gpd.GeoSeries([centro_proj], crs='EPSG:31983')
           .to_crs(epsg=4326)[0]
    )
    m = folium.Map(location=[centro_wgs84.y, centro_wgs84.x],
                   zoom_start=10, width="95%", height="800px")

    # 2. Cria um FeatureGroup pra cada categoria
    grupos = {}
    for cat in CORES.keys():
        grupos[cat] = folium.FeatureGroup(name=cat)
        m.add_child(grupos[cat])

    # 3. Adiciona cada geometria ao grupo correto
    for _, row in gdf.iterrows():
        fg = grupos[row['categoria']]
        folium.GeoJson(
            row.geometry,
            style_function=lambda feat, cat=row['categoria']: {
                'fillColor': CORES[cat],
                'color': 'black',
                'weight': 0.5,
                'fillOpacity': 0.7
            },
            tooltip=(
                f"<strong>Nome:</strong>{row['imovel']}<br>"
                f"<strong>Núm. INCRA:</strong>{row['numero_incra']}<br>"
                f"<strong>Situação:</strong>{row['situacao_juridica']}<br>"
                f"<strong>Município:</strong> {row['nome_municipio']}<br>"
                f"<strong>Distrito:</strong> {row['distrito']}<br>"
                f"<strong>Região Administrativa:</strong>{row['regiao_administrativa']}<br>"
                f"<strong>Área:</strong> {row['area']} ha<br>"
                f"<strong>Categoria:</strong> {row['categoria']}<br>"
            )
        ).add_to(fg)

    # 4. Legenda estática  e controle de camadas
    legend = f'''
      <div style="position: fixed; top: 150px; right: 150px; z-index:1000;
                  background:white; padding:10px; border:2px solid grey;
                  border-radius:5px; font-size:14px;">
        <strong>{regiao}</strong><br>
        {'<br>'.join([f'<i style="color:{c}">■</i> {cat}' 
            for cat,c in CORES.items()])}
      </div>
    '''
    m.get_root().html.add_child(folium.Element(legend))

    # 5. Adiciona o controle de camadas
    folium.LayerControl(collapsed=True).add_to(m)

    return m


# ————————————————————————————————————————————————————————————————————
def mostrar_mapa_regiao(data: pd.DataFrame, regiao: str):
    """Função principal que limpa, classifica e exibe o mapa."""
    clear_output(wait=True)
    display(dropdown)  # mantém o dropdown visível
    try:
        print(f"🔍 Processando região: {regiao}")
        gdf = carregar_dados_por_regiao(data, regiao)
        print(f"✅ Propriedades válidas: {len(gdf)}")
        print("📊 Distribuição:")
        print(gdf['categoria'].value_counts().to_string())
        print("🖱️ Gerando mapa…")
        mapa = criar_mapa_com_camadas(gdf, regiao)
        display(mapa)
    except Exception as e:
        print(f"❌ Erro: {e}")

# ————————————————————————————————————————————————————————————————————
# PIPELINE PRINCIPAL

# ————————————————————————————————————————————————————————————————————
#1.  pré-processa TUDO antes do dropdown existir
gdf_classificado = preprocessar_tudo(data.sample(10000))


# ————————————————————————————————————————————————————————————————————
# 2. Cria e exibe o dropdown
regioes = sorted(gdf_classificado['regiao_administrativa'].unique())
dropdown = widgets.Dropdown(
    options=regioes,
    description='Escolha a Região:',
    style={'description_width': 'initial'},
    layout=widgets.Layout(width='40%')
)
dropdown.observe(lambda change: mostrar_mapa_regiao(gdf_classificado, change.new), names='value')
display(dropdown)

#3. Exibe inicialmente
mostrar_mapa_regiao(gdf_classificado, regioes[0])
