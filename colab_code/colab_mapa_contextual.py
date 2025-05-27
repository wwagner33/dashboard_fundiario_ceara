# @title
import geopandas as gpd
import pandas as pd
import unicodedata
import json
import os


def get_latest_dataset():
    # Caminho da pasta onde estão os datasets
    pasta_datasets = 'data/' #/Projetos/2024-governanca-fundiaria/[DATA-TO-ANALYSIS]/

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

import folium
import geopandas as gpd
import pandas as pd
import unicodedata
import json
import random
from shapely.geometry import Point
from IPython.display import display, HTML
def preparar_dados(data: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Realiza a limpeza e preparação dos dados geográficos.

    Passos:
    1. Verifica se as colunas obrigatórias ('geom', 'area', 'modulo_fiscal') estão presentes.
    2. Remove registros com valores nulos nessas colunas.
    3. Filtra apenas registros com geometria do tipo 'MULTIPOLYGON'.
    4. Converte a coluna 'geom' de texto para objeto geométrico usando WKT.
    5. Simplifica as geometrias para melhorar o desempenho.
    6. Cria um GeoDataFrame com o CRS original e converte para EPSG:4326 (padrão para mapas).

    Parâmetros:
        data: DataFrame com dados originais.

    Retorna:
        GeoDataFrame com os dados geográficos preparados.
    """
    # Lista das colunas necessárias para a análise
    required_columns = ['geom', 'area', 'modulo_fiscal']

    # Verifica se todas as colunas requeridas estão presentes, caso contrário, lança um erro
    if not all(column in data.columns for column in required_columns):
        raise ValueError(f"O DataFrame deve conter as colunas: {required_columns}")

    # Remove linhas com valores nulos nas colunas críticas
    data = data.dropna(subset=required_columns)

    # Filtra registros cuja coluna 'geom' inicia com 'MULTIPOLYGON'
    data = data[data['geom'].str.startswith('MULTIPOLYGON')].copy()

    # Converte a string WKT em objeto geométrico usando shapely
    try:
        data['geometry'] = data['geom'].apply(wkt.loads)
    except Exception as e:
        raise ValueError(f"Erro ao converter geometrias: {e}")

    # Simplifica as geometrias para reduzir a complexidade sem perder a topologia
    data['geometry'] = data['geometry'].apply(simplificar_geometria)

    # Cria um GeoDataFrame e converte o sistema de referência para EPSG:4326 (latitude/longitude)
    gdf = gpd.GeoDataFrame(data, geometry='geometry', crs='EPSG:31984').to_crs(epsg=4326)

    return gdf

def classificar_propriedades(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classifica as propriedades em categorias com base na área e no módulo fiscal.

    Categorias definidas:
    - Pequena Propriedade < 1 MF: área > 0 e menor que um módulo fiscal.
    - Pequena Propriedade: área entre um módulo fiscal e 4 módulos fiscais.
    - Média Propriedade: área entre 4 e 15 módulos fiscais.
    - Grande Propriedade: área maior que 15 módulos fiscais.

    Parâmetros:
        df: GeoDataFrame com as colunas 'area' e 'modulo_fiscal'.

    Retorna:
        GeoDataFrame com uma nova coluna 'categoria' definida.
    """

    # Descartar propriedades com área ou módulo fiscal vazios
    df = df.dropna(subset=['area', 'modulo_fiscal'])

    # Descartar propriedades com área ou módulo fiscal iguais a zero
    df = df[(df['area'] != 0) & (df['modulo_fiscal'] != 0)]

    # Retornar None, caso não haja nenhuma propriedade com área e módulo fiscal válida
    if df.empty:
        return None, None

    cond_pequena_menor_1mf = (df['area'] > 0) & (df['area'] < 1 * df['modulo_fiscal'])
    cond_pequena    = (df['area'] >= 1 * df['modulo_fiscal']) & (df['area'] <= 4 * df['modulo_fiscal'])
    cond_media      = (df['area'] > 4 * df['modulo_fiscal']) & (df['area'] <= 15 * df['modulo_fiscal'])
    cond_grande     = (df['area'] > 15 * df['modulo_fiscal'])

    # cond_pequena_menor_1mf = (df['area'] > 0) & (df['area'] < 1*df['modulo_fiscal'])
    # cond_pequena = (df['area'] >= df['modulo_fiscal']) & (df['area'] <= 4 * df['modulo_fiscal'])
    # cond_media = (df['area'] > 4 * df['modulo_fiscal']) & (df['area'] <= 15 * df['modulo_fiscal'])
    # cond_grande = (df['area'] > 15 * df['modulo_fiscal'])
    df['categoria'] = None
    df.loc[cond_pequena_menor_1mf, 'categoria'] = 'Pequena Propriedade < 1 MF'
    df.loc[cond_pequena, 'categoria'] = 'Pequena Propriedade'
    df.loc[cond_media, 'categoria'] = 'Média Propriedade'
    df.loc[cond_grande, 'categoria'] = 'Grande Propriedade'
    antes = len(df)
    df = df.dropna(subset=['categoria'])
    depois = len(df)
    print("Propriedades classificadas com sucesso. Registros descartados:", antes - depois)
    return df

def format_number_br(num):
    """
    Formata um número para o padrão brasileiro (sem casas decimais):
      - Separador de milhares: ponto
      - Separador decimal: vírgula
    """
    formatted = f"{num:,.0f}"
    return formatted.replace(",", ".")

def criar_df_heatmap(data_classificada: pd.DataFrame, municipios_ce: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Agrupa as propriedades por município (apenas os registros classificados),
    e faz um merge com o DataFrame completo de municípios para garantir
    que todos os municípios sejam exibidos.
    Cria as colunas:
      - total: soma de todas as contagens
      - dominante: tipo com maior quantidade
    Retorna um GeoDataFrame.
    """
    contagem_propriedades = data_classificada.groupby(['nome_municipio', 'categoria']).size().unstack(fill_value=0)
    contagem_propriedades.reset_index(inplace=True)
    contagem_propriedades.rename(columns={
        'Pequena Propriedade < 1 MF': 'qtde_pequena_propriedade_menor_1_MF',
        'Pequena Propriedade': 'qtde_pequena_propriedade',
        'Média Propriedade': 'qtde_media_propriedade',
        'Grande Propriedade': 'qtde_grande_propriedade'
    }, inplace=True)

    df_heatmap = municipios_ce[['nome_municipio', 'geometry']].copy()
    df_heatmap = df_heatmap.merge(contagem_propriedades, on='nome_municipio', how='left')
    df_heatmap.fillna({
        'qtde_pequena_propriedade_menor_1_MF': 0,
        'qtde_pequena_propriedade': 0,
        'qtde_media_propriedade': 0,
        'qtde_grande_propriedade': 0
    }, inplace=True)
    print("Valores nulos preenchidos com 0 nas contagens de propriedades.")

    #df_heatmap.rename(columns={'geom_municipio': 'geometry'}, inplace=True)
    df_heatmap = gpd.GeoDataFrame(df_heatmap, geometry='geometry')
    df_heatmap.columns = df_heatmap.columns.astype(str)
    df_heatmap = df_heatmap.reset_index(drop=True)

    # Calcula a coluna 'total'
    df_heatmap['total'] = (
        df_heatmap['qtde_pequena_propriedade_menor_1_MF'].astype(int) +
        df_heatmap['qtde_pequena_propriedade'].astype(int) +
        df_heatmap['qtde_media_propriedade'].astype(int) +
        df_heatmap['qtde_grande_propriedade'].astype(int)
    )

    # Determina a categoria dominante para cada município
    def categoria_dominante(row):
        if row['total'] == 0:
            return "Sem Registro"
        contagens = {
            "Pequena Propriedade < 1 MF": row['qtde_pequena_propriedade_menor_1_MF'],
            "Pequena Propriedade": row['qtde_pequena_propriedade'],
            "Média Propriedade": row['qtde_media_propriedade'],
            "Grande Propriedade": row['qtde_grande_propriedade']
        }
        return max(contagens, key=contagens.get)

    df_heatmap['dominante'] = df_heatmap.apply(categoria_dominante, axis=1)
    print("Coluna 'dominante' criada com sucesso.")

    return df_heatmap


def criar_barra_opacidade(min_total, max_total):
    """
    Cria um HTML overlay que desenha uma barra horizontal,
    mostrando a variação de opacidade de 0.3 a 0.8,
    com alguns valores intermediários entre min_total e max_total.
    """
    # Define quantos "steps" queremos
    step_count = 6  # min, 4 steps intermediários, max
    if max_total <= min_total:
        # Caso degenerado
        step_labels = [format_number_br(min_total), format_number_br(max_total)]
    else:
        step_size = (max_total - min_total) / (step_count - 1)
        step_labels = []
        for i in range(step_count):
            val = min_total + i*step_size
            step_labels.append(format_number_br(val))

    # Cria a barra de gradiente (uma cor "cinza" com alpha de 0.3 a 0.8)
    # Depois exibimos os rótulos abaixo
    steps_html = ""
    for lbl in step_labels:
        steps_html += f"<span>{lbl}</span>"

    # Monta o HTML
    # Observação: É apenas ilustrativo, pois estamos usando cor cinza e alpha 0.3~0.8
    # mas no mapa real temos 4 cores dominantes. Então, esse gradiente é somente
    # para mostrar como a opacidade varia em função do total.
    overlay_html = f"""
    <div style="
        position: fixed;
        bottom: 50px;
        left: 50px;
        z-index: 1000;
        background-color: rgba(255,255,255,0.8);
        padding: 10px;
        border: 1px solid grey;
        border-radius: 5px;
        width: 250px;
        font-size: 14px;
    ">
      <p style="margin:0; padding:0;"><strong>Gradiente de Opacidade</strong></p>
      <div style="width:100%; height: 15px; margin-top:5px;
        background: linear-gradient(to right, rgba(136,136,136,0.3), rgba(136,136,136,0.8));
      "></div>
      <div style="display: flex; justify-content: space-between; margin-top: 5px;">
        {steps_html}
      </div>
      <p style="margin:0; padding:0; font-size:12px;">(Valores de propriedades: {format_number_br(min_total)} a {format_number_br(max_total)})</p>
    </div>
    """
    return overlay_html

def criar_choropleth_contextual(df_heatmap):
    """
    Cria um Choropleth Map contextual. Cada município é pintado de acordo com a 'dominante'
    e a opacidade varia com o total de propriedades.
    Munícipios sem registro => cor cinza, opacidade.
    """
    # cores = {
    #     "qtde_pequena_propriedade_menor_1_MF": "#3182bd",
    #     "Pequena Propriedade": "#31a354",
    #     "Média Propriedade": "#ffec08",
    #     "Grande Propriedade": "#FF6347",
    #     "Sem Registro": "#CCCCCC"
    # }

    cores = {
        "Pequena Propriedade < 1 MF": "#9b19f5",
        "Pequena Propriedade": "#0040bf",
        "Média Propriedade": "#e6d800",
        "Grande Propriedade": "#d97f00",
        "Sem Registro": "#9fa2a5"
    }

    min_total = df_heatmap['total'].min()
    max_total = df_heatmap['total'].max()

    mapa = folium.Map(location=[-5.2, -39.3], zoom_start=7, zoom_snap=0.25, zoom_delta=0.25)

    def style_function(feature):
        total = feature['properties']['total']
        if total == 0:
            # Sem registro
            norm_opacity = 0.4
        else:
            # Normaliza opacidade entre 0.4 e 0.9
            if max_total > min_total:
                norm_opacity = 0.4 + 0.5 * ((total - min_total)/(max_total - min_total))
            else:
                norm_opacity = 0.8
        domin = feature['properties']['dominante']
        return {
            'fillOpacity': norm_opacity,
            'weight': 0.3,
            'color': 'black',
            'fillColor': cores.get(domin, 'red')
        }

    # Camada de choropleth contextual
    folium.GeoJson(
        df_heatmap.to_json(),
        name="Choropleth Map Contextual",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=['nome_municipio', 'qtde_pequena_propriedade_menor_1_MF', 'qtde_pequena_propriedade',
                    'qtde_media_propriedade', 'qtde_grande_propriedade', 'total', 'dominante'],
            aliases=['Município:', 'Pequena Propriedade < 1 MF:', 'Pequena Propriedade:', 'Média Propriedade:', 'Grande Propriedade:', 'Total:', 'Dominante:'],
            localize=True
        )
    ).add_to(mapa)



    # Limites dos Municípios – show=True
    limites_fg = folium.FeatureGroup(name="Limites dos Municípios", show=True)
    folium.GeoJson(
        df_heatmap.to_json(),
        style_function=lambda feature: {
            'fillColor': 'none',
            'color': 'black',
            'weight': 1
        }
    ).add_to(limites_fg)
    limites_fg.add_to(mapa)



    # Título com subtítulo
    total_properties = df_heatmap['total'].sum()
    total_properties_formatted = format_number_br(total_properties)
    titulo_html = f"""
    <div style="
        position: fixed;
        top: 10px;
        left: 50px;
        z-index: 1000;
        background-color: rgba(255,255,255,0.9);
        padding: 10px;
        border: 1px solid grey;
        border-radius: 5px;
        font-size: 18px;
        font-weight: bold;
    ">
      Mapa de Densidade e Tipo de Propriedades Por Município do Ce<br>
      <span style="font-size:14px; font-weight:normal;">Total de Propriedades: {total_properties_formatted}</span>
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(titulo_html))

    # Legenda customizada
    legenda_html = f"""
    <div style="
        position: fixed;
        top: 120px;
        right: 50px;
        z-index: 1000;
        background-color: rgba(255,255,255,0.8);
        padding: 10px;
        border: 1px solid grey;
        border-radius: 5px;
        font-size: 14px;
    ">
      <p><strong>Legenda - Tipo Dominante</strong></p>
      <p><i style="background:{cores["Pequena Propriedade < 1 MF"]}; width: 10px; height: 10px; display: inline-block;"></i> Pequena Propriedade < 1 MF</p>
      <p><i style="background:{cores["Pequena Propriedade"]}; width: 10px; height: 10px; display: inline-block;"></i> Pequena Propriedade</p>
      <p><i style="background:{cores["Média Propriedade"]}; width: 10px; height: 10px; display: inline-block;"></i> Média Propriedade</p>
      <p><i style="background:{cores["Grande Propriedade"]}; width: 10px; height: 10px; display: inline-block;"></i> Grande Propriedade</p>
      <p><i style="background:{cores["Sem Registro"]}; width: 10px; height: 10px; display: inline-block;"></i> Sem Registro</p>
      <p><strong>Opacidade</strong> indica densidade (total de propriedades).</p>
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(legenda_html))
    # Barra de informação sobre a opacidade
    barra_html = criar_barra_opacidade(min_total, max_total)
    mapa.get_root().html.add_child(folium.Element(barra_html))

    # Adiciona o controle de camadas (apenas a camada dos Limites aparecerá para controle)
    # folium.LayerControl(collapsed=False).add_to(mapa)
    folium.LayerControl().add_to(mapa)

    return mapa

def main():
    # if dados_combinados is None or data is None or municipios_ce is None:
    #     print("Erro ao carregar os dados.")
    #     return None

    # Quantidade total de municípios no DataFrame (ex.: 184)
    total_municipios_ce = len(municipios_ce)
    # Quantos municípios têm pelo menos 1 registro no dataset "data"
    municipios_com_propriedade = len(data['nome_municipio'].unique())

    # Classifica as propriedades; registros sem categoria são descartados
    registros_iniciais = len(data)
    try:
        dados_classificados = classificar_propriedades(data)
        registros_classificados = len(dados_classificados)
        descartados_categoria = registros_iniciais - registros_classificados
    except Exception as e:
        print(f"Erro ao classificar as propriedades: {e}")
        return None

    # Cria o GeoDataFrame agregado
    try:
        df_heatmap = criar_df_heatmap(dados_classificados, municipios_ce)
    except Exception as e:
        print(f"Erro ao criar o dataset final para o Choropleth: {e}")
        return None

    # Soma dos totais dos municípios
    total_registros_utilizados = int(df_heatmap['total'].sum())
    # Quantidade de municípios (linhas) no df_heatmap (deve ser 184)
    municipios_utilizados = len(df_heatmap)

        # Calcula a quantidade de municípios por dominância
    dominancia = df_heatmap['dominante'].value_counts()
    pequena_propriedade_m_1mf_count = dominancia.get("Pequena Propriedade < 1 MF", 0)
    pequena_count = dominancia.get("Pequena Propriedade", 0)
    media_count = dominancia.get("Média Propriedade", 0)
    grande_count = dominancia.get("Grande Propriedade", 0)
    sem_registro_count = dominancia.get("Sem Registro", 0)

    # Monta a tabela de estatísticas
    stats = {
        'Descrição': [
            "Quantidade de Propriedades lidas do Dataset 'data'",
            "Quantidade de registros descartados por falta de categoria",
            "Quantidade total de municípios do Ceará (municipios_ce)",
            "Quantidade de municípios com pelo menos um registro (em data)",
            "Quantidade de municípios no mapa (df_heatmap)",
            "Quantidade de Propriedades efetivamente utilizadas (soma dos totais)",
            "Municípios com Dominância de Pequenas Propriedades < 1 MF",
            "Municípios com Dominância de Pequenas Propriedades",
            "Municípios com Dominância de Médias Propriedades",
            "Municípios com Dominância de Grandes Propriedades",
            "Municípios sem registro de propriedades"
        ],
        'Quantidade': [
            len(data),
            descartados_categoria,
            total_municipios_ce,
            municipios_com_propriedade,
            municipios_utilizados,
            total_registros_utilizados,
            pequena_propriedade_m_1mf_count,
            pequena_count,
            media_count,
            grande_count,
            sem_registro_count
        ]
    }
    df_stats = pd.DataFrame(stats)

    # Cria o Mapa contextual
    try:
        mapa = criar_choropleth_contextual(df_heatmap)
        print("Choropleth contextual criado com sucesso.")
    except Exception as e:
        print(f"Erro ao criar o mapa: {e}")
        return None

    # Exibe o mapa
    print("Mapa gerado com sucesso. Apresentando o mapa: \n")
    display(mapa)

    # Exibe a tabela de estatísticas depois do mapa
    print("Tabela de Estatísticas:\n")
    display(df_stats)

    return mapa

# Executa o pipeline
malha_fundiaria_ceara = main()