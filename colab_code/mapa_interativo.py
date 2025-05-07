# @title
import unicodedata
import json
import geopandas as gpd         # Manipulação de dados geográficos
import pandas as pd            # Manipulação de DataFrames
import numpy as np             # Manipulação de arrays e matrizes
import folium                 # Criação de mapas interativos
import json                   # Leitura de arquivos JSON
from shapely import wkt       # Conversão de strings WKT para objetos geométricos
from folium.plugins import MarkerCluster  # Plugin para agrupar marcadores próximos

from google.colab import drive
import os

# Monta o Google Drive no local padrão
drive.mount('/content/drive')

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
    try:
        municipios_ce = gpd.read_file('/content/drive/My Drive/Projetos/2024-governanca-fundiaria/[DATA-TO-ANALYSIS]/data_to_colab/geojson-municipios_ceara-normalizado.geojson')
        print("GeoJSON dos municípios carregado com sucesso.")
    except Exception as e:
        print(f"Erro ao carregar o GeoJSON dos municípios: {e}")
        return None, None

    if 'properties' in municipios_ce.columns:
        props = pd.json_normalize(municipios_ce['properties'])
        municipios_ce = municipios_ce.drop(columns=['properties']).join(props)
        print("Propriedades extraídas e unidas ao DataFrame dos municípios.")

    try:
        data = pd.read_csv('/content/drive/My Drive/Projetos/2024-governanca-fundiaria/[DATA-TO-ANALYSIS]/data_to_colab/dataset-malha-fundiaria-idace_preprocessado-2025-04-26.csv', low_memory=False)
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



# Ativa o gerenciador de widgets customizados (para melhorar a exibição no Colab)
output.enable_custom_widget_manager()

def simplificar_geometria(geometry, tolerance=0.01):
    """
    Simplifica uma geometria usando o algoritmo de Douglas-Peucker.

    Parâmetros:
        geometry: objeto geométrico a ser simplificado.
        tolerance (float): tolerância para a simplificação. Quanto maior, mais simples fica.

    Retorna:
        Geometria simplificada, preservando a topologia.
    """
    return geometry.simplify(tolerance, preserve_topology=True)

def preparar_dados(data: pd.DataFrame) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """
    Realiza a limpeza e preparação dos dados geográficos com relatório completo de descartes.

    Parâmetros:
        data: DataFrame com dados originais

    Retorna:
        tuple: (GeoDataFrame preparado, DataFrame com registros descartados e motivos)
    """
    required_columns = ['geom', 'area', 'modulo_fiscal']
    total_inicial = len(data)

    # Verifica colunas obrigatórias
    if not all(column in data.columns for column in required_columns):
        raise ValueError(f"O DataFrame deve conter as colunas: {required_columns}")

    # Cria cópia para rastrear descartes
    data_com_motivos = data.copy()
    data_com_motivos['motivo_descarte'] = None

    # Identifica problemas
    # 1. Verifica valores nulos
    nulos_area = data['area'].isna()
    nulos_modulo = data['modulo_fiscal'].isna()
    nulos_geom = data['geom'].isna()

    data_com_motivos.loc[nulos_area, 'motivo_descarte'] = 'Área nula'
    data_com_motivos.loc[nulos_modulo, 'motivo_descarte'] = 'Módulo fiscal nulo'
    data_com_motivos.loc[nulos_geom, 'motivo_descarte'] = 'Geometria nula'

    # 2. Verifica zeros (após remover nulos)
    dados_sem_nulos = data.dropna(subset=required_columns)
    mask_area_zero = (dados_sem_nulos['area'] == 0)
    mask_modulo_zero = (dados_sem_nulos['modulo_fiscal'] == 0)

    idx_area_zero = dados_sem_nulos[mask_area_zero].index
    idx_modulo_zero = dados_sem_nulos[mask_modulo_zero].index
    idx_ambos_zero = dados_sem_nulos[mask_area_zero & mask_modulo_zero].index

    data_com_motivos.loc[idx_area_zero, 'motivo_descarte'] = 'Área igual a zero'
    data_com_motivos.loc[idx_modulo_zero, 'motivo_descarte'] = 'Módulo fiscal igual a zero'
    data_com_motivos.loc[idx_ambos_zero, 'motivo_descarte'] = 'Área e módulo fiscal iguais a zero'

    # 3. Verifica tipo de geometria
    dados_validos = dados_sem_nulos[(dados_sem_nulos['area'] > 0) &
                                  (dados_sem_nulos['modulo_fiscal'] > 0)].copy()

    mask_geometria_invalida = ~dados_validos['geom'].str.startswith('MULTIPOLYGON', na=False)
    idx_geometria_invalida = dados_validos[mask_geometria_invalida].index
    data_com_motivos.loc[idx_geometria_invalida, 'motivo_descarte'] = 'Geometria não MULTIPOLYGON'

    # Separa dados descartados
    descartes = data_com_motivos[data_com_motivos['motivo_descarte'].notnull()].copy()

    # Processa dados válidos
    dados_validos = dados_validos[~mask_geometria_invalida]
    try:
        dados_validos['geometry'] = dados_validos['geom'].apply(wkt.loads)
        dados_validos['geometry'] = dados_validos['geometry'].apply(simplificar_geometria)
    except Exception as e:
        raise ValueError(f"Erro ao converter geometrias: {e}")

    gdf = gpd.GeoDataFrame(dados_validos, geometry='geometry', crs='EPSG:31984').to_crs(epsg=4326)
    total_valido = len(gdf)

    # Gera relatório detalhado
    if not descartes.empty:
        print("\nRELATÓRIO COMPLETO DE PROCESSAMENTO")
        print("==================================")
        print(f"Total de registros recebidos: {total_inicial}")
        print(f"Total de registros válidos após processamento: {total_valido}")
        print(f"Total de registros descartados: {len(descartes)}")
        print("\nDetalhamento dos descartes:")

        contagem = descartes['motivo_descarte'].value_counts()
        print("\n".join([f"  - {motivo}: {quantidade} registros"
                       for motivo, quantidade in contagem.items()]))

        print(f"\nTaxa de aproveitamento: {total_valido/total_inicial:.1%}")

        # Opcional: salva descartes em arquivo para análise
        try:
            descartes.to_csv('registros_descartados.csv', index=False)
            print("\nDetalhes completos dos registros descartados salvos em 'registros_descartados.csv'")
        except Exception as e:
            print(f"\nNão foi possível salvar arquivo de descartes: {e}")

    return gdf, descartes

def classificar_propriedades(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classifica as propriedades em categorias com base na área e módulo fiscal.

    Parâmetros:
        df: GeoDataFrame já preparado (sem valores nulos/zeros)

    Retorna:
        GeoDataFrame com coluna 'categoria' adicionada
    """
    # Classificação
    conditions = [
        (df['area'] < 1 * df['modulo_fiscal']),
        (df['area'] >= 1 * df['modulo_fiscal']) & (df['area'] <= 4 * df['modulo_fiscal']),
        (df['area'] > 4 * df['modulo_fiscal']) & (df['area'] <= 15 * df['modulo_fiscal']),
        (df['area'] > 15 * df['modulo_fiscal'])
    ]
    categories = ['Minifundio', 'Pequena Propriedade', 'Média Propriedade', 'Grande Propriedade']

    df['categoria'] = np.select(conditions, categories, default=None)

    # Estatísticas de classificação
    categoria_counts = df['categoria'].value_counts()
    categoria_str = "\n".join([f"      - {cat}: {count}" for cat, count in categoria_counts.items()])

    print(f"""DISTRIBUIÇÃO POR CATEGORIA:\n{categoria_str}""")

    return df.dropna(subset=['categoria'])


def criar_mapa(gdf: gpd.GeoDataFrame, municipios_ce: gpd.GeoDataFrame) -> folium.Map:
    """
    Cria um mapa interativo com:
    - Camada de municípios (bordas dos polígonos)
    - Camadas de propriedades classificadas por tamanho
    - Controles de camadas para alternar entre as visualizações
    """
    # Inicializa o mapa
    mapa = folium.Map(location=[-5.2, -39.3], zoom_start=8)

    # Adiciona camada de municípios (apenas bordas)
    folium.GeoJson(
        data=municipios_ce.to_json(),
        style_function=lambda feature: {
            'fillColor': 'transparent',
            'color': '#000000',
            'weight': 1,
            'fillOpacity': 0
        },
        name='Municípios (contornos)',
        tooltip=folium.GeoJsonTooltip(
            fields=['nome_municipio'],
            aliases=['Município:'],
            localize=True
        )
    ).add_to(mapa)

    # Cores para as categorias de propriedades
    cores = {
        'Minifundio': '#9b19f5',
        'Pequena Propriedade': '#0040bf',
        'Média Propriedade': '#e6d800',
        'Grande Propriedade': '#d97f00'
    }

    # Adiciona camadas para cada categoria de propriedade
    for categoria, cor in cores.items():
        gdf_categoria = gdf[gdf['categoria'] == categoria]

        if not gdf_categoria.empty:
            folium.GeoJson(
                data=gdf_categoria.to_json(),
                style_function=lambda feature, cor=cor: {
                    'fillColor': cor,
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0.7
                },
                name=categoria,
                tooltip=folium.GeoJsonTooltip(
                    fields=["nome_municipio", "imovel", "area", "modulo_fiscal", "categoria"],
                    aliases=["Município", "Imóvel", "Área (ha)", "Módulo Fiscal", "Categoria"],
                    localize=True,
                    sticky=False,
                    labels=True,
                    style="""
                        background-color: #F0EFEF;
                        border: 2px solid black;
                        border-radius: 3px;
                        box-shadow: 3px;
                        text-wrap: pretty;
                    """,
                    max_width=400,
                )
            ).add_to(mapa)

    # Adiciona controle de camadas
    folium.LayerControl().add_to(mapa)

    # Legenda e título (mantidos da versão anterior)
    legenda_html = """
    <div style="
        position: fixed;
        top: 50px;
        right: 100px;
        z-index: 1000;
        background-color: white;
        padding: 10px;
        border: 2px solid grey;
        border-radius: 5px;
        font-size: 14px;
    ">
        <p><strong>Tipos de Propriedades</strong></p>
    """
    for categoria, cor in cores.items():
        legenda_html += f"""
        <p><i class="fa fa-square" style="color: {cor};"></i> {categoria}</p>
        """
    legenda_html += """
        <p><i class="fa fa-square" style="color: #000000;"></i> Contornos Municipais</p>
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(legenda_html))

    titulo_html = """
    <div style="
        position: fixed;
        top: 10px;
        left: 50px;
        z-index: 1000;
        background-color: white;
        padding: 10px;
        border: 2px solid grey;
        border-radius: 5px;
        font-size: 18px;
        font-weight: bold;
    ">
        Malha Fundiária do Ceará
        <div style="font-size: 14px;">
          Lotes classificados com base em suas áreas
        </div>
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(titulo_html))

    return mapa

def pipeline(data: pd.DataFrame, municipios_ce: gpd.GeoDataFrame):
    """
    Pipeline principal atualizado:
    1. Prepara os dados
    2. Classifica as propriedades
    3. Cria o mapa com ambas as camadas
    """
    # Prepara os dados
    gdf, _ = preparar_dados(data)

    # Classifica as propriedades
    gdf_classificado = classificar_propriedades(gdf)

    # Cria o mapa com os municípios e propriedades
    mapa = criar_mapa(gdf_classificado, municipios_ce)
    return mapa

try:
    malha_fundiaria_ceara = pipeline(data.sample(100000), municipios_ce)
    malha_fundiaria_ceara.save('mapa_malha_fundiaria.html')
    display(malha_fundiaria_ceara)
except Exception as e:
    print(f"Erro ao gerar o mapa: {e}")

