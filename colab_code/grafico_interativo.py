# @title
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from ipywidgets import Dropdown, VBox, HBox, Output, HTML as WidgetHTML
from IPython.display import display, HTML

from google.colab import drive
drive.mount('/content/drive')

# # Caminho do arquivo no Google Drive
# file_path = '/content/drive/MyDrive/Projetos/2024-governanca-fundiaria/[DATA-TO-ANALYSIS]/data_to_colab/dataset-malha-fundiaria-idace_preprocessado-2025-03-21-19-29-16.csv'

# # Carregar o arquivo CSV
# data = pd.read_csv(file_path, low_memory=False)



def get_latest_dataset():
    # Caminho da pasta onde estão os datasets
    pasta_datasets = '/content/drive/MyDrive/Projetos/2024-governanca-fundiaria/[DATA-TO-ANALYSIS]/data_to_colab/'

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

# Carga do dataset mais atual
caminho_dataset = get_latest_dataset()
try:
  data = pd.read_csv(caminho_dataset, low_memory=False)
  print(f"Dataset carregado com sucesso: {caminho_dataset}")
except Exception as e:
  print(f"Erro ao carregar o dataset: {e}")


def classificar_propriedades(df):
    """
    Adiciona uma coluna 'tipo_propriedade' classificando as propriedades:
        1. Minifúndio: 0 < área < 1 MF
        2. Pequena Propriedade: 1 MF ≤ área ≤ 4 MF
        3. Média Propriedade: 4 MF < área ≤ 15 MF
        4. Grande Propriedade: área > 15 MF
    Retorna o dataframe atualizado.
    """

    if df.empty:
        return None

    # Condições
    cond_minifundio = (df['area'] > 0) & (df['area'] < 1 * df['modulo_fiscal'])
    cond_pequena    = (df['area'] >= 1 * df['modulo_fiscal']) & (df['area'] <= 4 * df['modulo_fiscal'])
    cond_media      = (df['area'] > 4 * df['modulo_fiscal']) & (df['area'] <= 15 * df['modulo_fiscal'])
    cond_grande     = (df['area'] > 15 * df['modulo_fiscal'])

    # Inicializa como string vazia
    df['tipo_propriedade'] = ''

    # Preenche de acordo com a classificação
    df.loc[cond_minifundio, 'tipo_propriedade'] = 'Minifúndio'
    df.loc[cond_pequena,    'tipo_propriedade'] = 'Pequena Propriedade'
    df.loc[cond_media,      'tipo_propriedade'] = 'Média Propriedade'
    df.loc[cond_grande,     'tipo_propriedade'] = 'Grande Propriedade'

    # Corrige propriedades que não foram classificadas
    df['tipo_propriedade'] = df['tipo_propriedade'].replace('', 'Não Classificado')

    return df


# Classificar propriedades
data_classificado = classificar_propriedades(data.copy())

# Agora vamos contar quantos de cada tipo existem por região
contagem = (data_classificado
            .groupby(['regiao_administrativa', 'tipo_propriedade'])
            .size()
            .reset_index(name='quantidade'))

# Salvar o resultado no CSV
contagem.to_csv('classificacao_propriedades_por_regiao.csv', index=False)

# Mostrar o resultado
display(contagem)

# print(data_classificado.head())

# =============================================================================
# Funções de Filtragem e Classificação
# =============================================================================

def filtrar_dados(data, filtro, entidade):
    """
    Filtra o DataFrame 'data' conforme o tipo de filtro:
      - "Municípios": filtra pelo nome do município.
      - "Regiões Administrativas": filtra pela região administrativa.
      - "Todo o Estado": retorna todos os dados.
    """
    if filtro == "Municípios":
        return data[data['nome_municipio'] == entidade]
    elif filtro == "Regiões Administrativas":
        return data[data['regiao_administrativa'] == entidade]
    elif filtro == "Todo o Estado":
        return data
    return pd.DataFrame()

def classificar_propriedades(df):
    """
    Classifica as propriedades com base em seu tamanho em relação ao módulo fiscal de cada registro:
        1. Minifúndio: 0 < àrea < 1MF
        2. Pequena Propriedade: 1 MF ≤ àrea ≤ 4 MF
        3. Média Propriedade: 4 MF < àrea ≤ 15 MF
        4. Grande Propriedade: àrea >15 MF
    Retorna um dicionário com a contagem exata de propriedades em cada categoria e o total.
    """

    # Descartar propriedades com área ou módulo fiscal vazios
    df = df.dropna(subset=['area', 'modulo_fiscal'])

    # Descartar propriedades com área ou módulo fiscal iguais a zero
    df = df[(df['area'] != 0) & (df['modulo_fiscal'] != 0)]

    # Retornar None, caso não haja nenhuma propriedade com área e módulo fiscal válida
    if df.empty:
        return None, None

    cond_minifundio = (df['area'] > 0) & (df['area'] < 1 * df['modulo_fiscal'])
    cond_pequena    = (df['area'] >= 1 * df['modulo_fiscal']) & (df['area'] <= 4 * df['modulo_fiscal'])
    cond_media      = (df['area'] > 4 * df['modulo_fiscal']) & (df['area'] <= 15 * df['modulo_fiscal'])
    cond_grande     = (df['area'] > 15 * df['modulo_fiscal'])

    resultados = {
        "Minifundio": int(cond_minifundio.sum()),
        "Pequena Propriedade": int(cond_pequena.sum()),
        "Média Propriedade": int(cond_media.sum()),
        "Grande Propriedade": int(cond_grande.sum())
    }
    total = len(df)
    return resultados, total

# =============================================================================
# Função para Exibir Informações em Tabela (Classificação)
# =============================================================================

def display_info_table(titulo, subtitulo, total, resultados):
    """
    Exibe as informações de classificação em uma tabela HTML estilizada.
    """
    info_html = f"""
    <div style="margin-bottom:20px;">
      <table style="width:50%; border-collapse: collapse; margin: auto; box-shadow: 0px 0px 8px rgba(0,0,0,0.1);">
        <caption style="caption-side: top; font-size: 18px; font-weight: bold; padding: 10px;">
          {titulo}<br>
          <span style="font-size: 14px; font-weight: normal;">{subtitulo}</span>
        </caption>
        <thead>
          <tr style="background-color: #836FFF;">
            <th style="padding: 8px; border: 1px solid #fff;">Categoria</th>
            <th style="padding: 8px; border: 1px solid #fff;">Valor</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">Minifúndio</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{resultados.get("Minifundio", 0)}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">Pequena Propriedade</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{resultados.get("Pequena Propriedade", 0)}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">Média Propriedade</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{resultados.get("Média Propriedade", 0)}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">Grande Propriedade</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{resultados.get("Grande Propriedade", 0)}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">Total de Propriedades</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{total}</td>
          </tr>
        </tbody>
      </table>
    </div>
    """
    display(HTML(info_html))

# =============================================================================
# Funções de Plotagem
# =============================================================================

# Add this near the top of the code (with other constants)
cores = {
    "Minifúndio": "#9b19f5",
    "Pequena Propriedade": "#0040bf",
    "Média Propriedade": "#e6d800",
    "Grande Propriedade": "#d97f00",
    "Sem Registro": "#9fa2a5"
}

# Modify the plot_barras function:
def plot_barras(resultados, titulo, subtitulo):
    """
    Plota gráfico de barras com os valores e anota os totais acima de cada barra.
    """
    # Map category names to colors
    color_map = {
        "Minifundio": cores["Minifúndio"],
        "Pequena Propriedade": cores["Pequena Propriedade"],
        "Média Propriedade": cores["Média Propriedade"],
        "Grande Propriedade": cores["Grande Propriedade"]
    }

    # Get colors in correct order
    colors = [color_map[cat] for cat in resultados.keys()]

    plt.figure(figsize=(12, 8))
    bars = plt.bar(resultados.keys(), resultados.values(), color=colors, edgecolor='black', alpha=0.85)
    plt.title(f"{titulo}\n{subtitulo}", fontsize=16)
    plt.xlabel("Categoria", fontsize=14)
    plt.ylabel("Número de Propriedades", fontsize=14)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.xticks(rotation=45, fontsize=12)

    for bar in bars:
        height = bar.get_height()
        plt.annotate(f'{int(height)}',
                     xy=(bar.get_x() + bar.get_width()/2, height),
                     xytext=(0, 3),
                     textcoords="offset points",
                     ha='center', va='bottom')
    plt.tight_layout()
    plt.show()

# Modify the plot_pizza function:
def plot_pizza(resultados, titulo, subtitulo):
    """
    Plota gráfico de pizza com percentuais e legenda.
    Esse gráfico é tão gostoso quanto uma fatia de pizza (sem exageros, ok?).
    """
    # Map category names to colors
    color_map = {
        "Minifundio": cores["Minifúndio"],
        "Pequena Propriedade": cores["Pequena Propriedade"],
        "Média Propriedade": cores["Média Propriedade"],
        "Grande Propriedade": cores["Grande Propriedade"]
    }

    # Get colors in correct order
    colors = [color_map[cat] for cat in resultados.keys()]

    plt.figure(figsize=(10, 10))
    wedges, texts, autotexts = plt.pie(list(resultados.values()),
                                       labels=None,
                                       autopct='%1.1f%%',
                                       startangle=90,
                                       colors=colors,
                                       pctdistance=0.8)
    plt.title(f"{titulo}\n{subtitulo}", fontsize=16)
    plt.axis('equal')
    plt.legend(wedges, resultados.keys(), title="Tipos de Propriedade",
               loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    plt.tight_layout()
    plt.show()

# =============================================================================
# Função para Exibir Estatísticas Adicionais em Tabela
# =============================================================================

def display_stats_table(data):
    """
    Exibe uma tabela com estatísticas adicionais do dataset da Malha Fundiária.
    É como o "por trás das câmeras" que revela todos os segredos!
    """
    total_properties = len(data)
    missing_area = data['area'].isna().sum()
    missing_modulo = data['modulo_fiscal'].isna().sum()

    valid_data = data.dropna(subset=['area', 'modulo_fiscal'])
    valid_data = valid_data[(valid_data['area'] != 0) & (valid_data['modulo_fiscal'] != 0)]
    valid_data = valid_data[valid_data['nome_municipio'].notna()]
    total_valid = len(valid_data)

    total_municipios = len(data['nome_municipio'].dropna().unique())
    valid_municipios = len(valid_data['nome_municipio'].dropna().unique())

    # Classificação por município (para determinar a categoria dominante)
    conditions = [
        (valid_data['area'] > 0) & (valid_data['area'] < 1 * valid_data['modulo_fiscal']),
        (valid_data['area'] >= 1 * valid_data['modulo_fiscal']) & (valid_data['area'] <= 4 * valid_data['modulo_fiscal']),
        (valid_data['area'] > 4 * valid_data['modulo_fiscal']) & (valid_data['area'] <= 15 * valid_data['modulo_fiscal']),
        (valid_data['area'] > 15 * valid_data['modulo_fiscal'])
    ]
    choices = ["Minifundio", "Pequena Propriedade", "Média Propriedade", "Grande Propriedade"]
    valid_data = valid_data.copy()
    valid_data['categoria'] = np.select(conditions, choices, default="NaoClassificado")

    # Determinar a categoria dominante para cada município
    dominancia = valid_data.groupby('nome_municipio')['categoria'].agg(lambda x: x.value_counts().idxmax())
    dominancia_counts = dominancia.value_counts()
    dom_minifundio = dominancia_counts.get("Minifundio", 0)
    dom_pequena = dominancia_counts.get("Pequena Propriedade", 0)
    dom_media = dominancia_counts.get("Média Propriedade", 0)
    dom_grande = dominancia_counts.get("Grande Propriedade", 0)

    # Determinar o número de propriedades com áreaiguala zero
    zero_area = (data['area'] == 0).sum()

    # Determinar a quantidade de propriedades com informação do nome do município faltando ou vazia
    missing_municipio = data['nome_municipio'].isna().sum()

    stats = {
        "Propriedades lidas do Dataset": total_properties,
        "Propriedades descartados por falta de Àreas": missing_area,
        "Propriedades descartados por falta de Módulos Fiscais do Municípios": missing_modulo,
        "Propriedades descartasda por Áreas igual a zero": zero_area,
        "Propriedades descartadas por falta de município": missing_municipio,
        "Propriedades efetivamente utilizadas": total_valid,
        "Municípios c/ Dominância de Minifúndios": dom_minifundio,
        "Municípios c/ Dominância de Pequenas Propriedades": dom_pequena,
        "Municípios c/ Dominância de Médias Propriedades": dom_media,
        "Municípios c/ Dominância de Grandes Propriedades": dom_grande
    }

    stats_html = f"""
    <div style="margin-top:20px;">
      <table style="width:70%; border-collapse: collapse; margin: auto; box-shadow: 0px 0px 8px rgba(0,0,0,0.1);">
        <caption style="caption-side: top; font-size: 18px; font-weight: bold; padding: 10px;">
          Estatísticas Adicionais
        </caption>
        <thead>
          <tr style="background-color: #20B2AA;">
            <th style="padding: 8px; border: 1px solid #fff;">Métrica</th>
            <th style="padding: 8px; border: 1px solid #fff;">Valor</th>
          </tr>
        </thead>
        <tbody>
    """
    for key, value in stats.items():
        stats_html += f"""
          <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">{key}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{value}</td>
          </tr>
        """
    stats_html += """
        </tbody>
      </table>
    </div>
    """
    display(HTML(stats_html))

# =============================================================================
# Função Principal de Plotagem e Exibição
# =============================================================================

def plot_resultado(data, filtro, entidade, tipo_grafico):
    df_filtrado = filtrar_dados(data, filtro, entidade)
    classificacao, total = classificar_propriedades(df_filtrado)

    if classificacao is None:
        display(HTML(f"<p style='color:red;'>Propriedade registrada para {filtro} {entidade if entidade else ''}.</p>"))
        return

    if filtro == "Municípios":
        titulo = f"Classificação de Propriedades no Município '{entidade}'"
        subtitulo = f"Total de Propriedades: {total}"
    elif filtro == "Regiões Administrativas":
        titulo = f"Classificação de Propriedades na Região Administrativa '{entidade}'"
        subtitulo = f"Total de Propriedades: {total}"
    elif filtro == "Todo o Estado":
        titulo = "Classificação de Propriedades em Todo o Estado"
        subtitulo = f"Total de Propriedades: {total}"
    else:
        titulo, subtitulo = "Classificação de Propriedades", ""

    # Exibe a tabela de classificação (antes do gráfico)
    display_info_table(titulo, subtitulo, total, classificacao)

    # Exibe o gráfico (Barras ou Pizza)
    if tipo_grafico == "Barras":
        plot_barras(classificacao, titulo, subtitulo)
    elif tipo_grafico == "Pizza":
        plot_pizza(classificacao, titulo, subtitulo)

    # Exibe a tabela com estatísticas adicionais após o gráfico
    display_stats_table(data)

# =============================================================================
# Interface Interativa com ipywidgets
# =============================================================================

def create_interface(data):
    # Use WidgetHTML aqui para widgets
    filtro_title = WidgetHTML("<h3>Definir a exibição dos dados</h3>")

    municipios = sorted(data['nome_municipio'].dropna().unique())
    regioes = sorted(data['regiao_administrativa'].dropna().unique())

    dropdown_tipo = Dropdown(
        options=["Todo o Estado", "Municípios", "Regiões Administrativas"],
        value="Todo o Estado",
        description="Mostrar por:",
        style={'description_width': 'initial'}
    )

    dropdown_entidade = Dropdown(
        description="Selecionar Entidade:",
        style={'description_width': 'initial'}
    )

    dropdown_grafico = Dropdown(
        options=["Barras", "Pizza"],
        value="Barras",
        description="Tipo de Gráfico:",
        style={'description_width': 'initial'}
    )

    controls_box = VBox([filtro_title, dropdown_tipo, dropdown_entidade, dropdown_grafico])
    output = Output()

    def update_entidade(*args):
        filtro = dropdown_tipo.value
        if filtro == "Municípios":
            dropdown_entidade.options = municipios
            dropdown_entidade.value = municipios[0] if municipios else None
            dropdown_entidade.disabled = False
        elif filtro == "Regiões Administrativas":
            dropdown_entidade.options = regioes
            dropdown_entidade.value = regioes[0] if regioes else None
            dropdown_entidade.disabled = False
        else:
            dropdown_entidade.options = []
            dropdown_entidade.disabled = True

    def update_plot(*args):
        with output:
            output.clear_output()
            filtro = dropdown_tipo.value
            entidade = dropdown_entidade.value if not dropdown_entidade.disabled else None
            tipo_grafico = dropdown_grafico.value
            plot_resultado(data, filtro, entidade, tipo_grafico)

    dropdown_tipo.observe(lambda change: (update_entidade(), update_plot()), names='value')
    dropdown_entidade.observe(lambda change: update_plot(), names='value')
    dropdown_grafico.observe(lambda change: update_plot(), names='value')

    update_entidade()
    update_plot()

    main_box = HBox([controls_box, output])
    display(main_box)
    #data.to_csv("/content/drive/MyDrive/Projetos/2024-governanca-fundiaria/[DATA-TO-ANALYSIS]/data_to_colab/dataset-malha-fundiaria-idace_preprocessado-2025-04-10.csv",index=False)


# =============================================================================
# Execução da Interface
# =============================================================================

create_interface(data)


import pandas as pd

def classificar_propriedades(df):
    """
    Adiciona uma coluna 'tipo_propriedade' classificando as propriedades:
        1. Minifúndio: 0 < área < 1 MF
        2. Pequena Propriedade: 1 MF ≤ área ≤ 4 MF
        3. Média Propriedade: 4 MF < área ≤ 15 MF
        4. Grande Propriedade: área > 15 MF
    Retorna o dataframe atualizado.
    """

    if df.empty:
        return None

    # Condições
    cond_minifundio = (df['area'] > 0) & (df['area'] < 1 * df['modulo_fiscal'])
    cond_pequena    = (df['area'] >= 1 * df['modulo_fiscal']) & (df['area'] <= 4 * df['modulo_fiscal'])
    cond_media      = (df['area'] > 4 * df['modulo_fiscal']) & (df['area'] <= 15 * df['modulo_fiscal'])
    cond_grande     = (df['area'] > 15 * df['modulo_fiscal'])

    # Inicializa como string vazia
    df['tipo_propriedade'] = ''

    # Preenche de acordo com a classificação
    df.loc[cond_minifundio, 'tipo_propriedade'] = 'Minifúndio'
    df.loc[cond_pequena,    'tipo_propriedade'] = 'Pequena Propriedade'
    df.loc[cond_media,      'tipo_propriedade'] = 'Média Propriedade'
    df.loc[cond_grande,     'tipo_propriedade'] = 'Grande Propriedade'

    # Corrige propriedades que não foram classificadas
    df['tipo_propriedade'] = df['tipo_propriedade'].replace('', 'Não Classificado')

    return df


# Classificar propriedades
data_classificado = classificar_propriedades(data.copy())

# Agora vamos contar quantos de cada tipo existem por região
contagem = (data_classificado
            .groupby(['regiao_administrativa', 'tipo_propriedade'])
            .size()
            .reset_index(name='quantidade'))

# Salvar o resultado no CSV
contagem.to_csv('classificacao_propriedades_por_regiao.csv', index=False)

# Mostrar o resultado
display(contagem)

# print(data_classificado.head())

def contar_propriedades_por_regiao(data):
    """
    Gera um DataFrame com a contagem de propriedades por categoria
    (Minifúndio, Pequena, Média, Grande) para cada região administrativa.
    Inclui também o total de propriedades por região.
    """

    # Eliminar registros com dados faltantes ou inválidos
    df = data.dropna(subset=['area', 'modulo_fiscal', 'regiao_administrativa']).copy()
    df = df[(df['area'] > 0) & (df['modulo_fiscal'] > 0)]

    # Criar coluna de categoria de propriedade
    condicoes = [
        (df['area'] < 1 * df['modulo_fiscal']),
        (df['area'] >= 1 * df['modulo_fiscal']) & (df['area'] <= 4 * df['modulo_fiscal']),
        (df['area'] > 4 * df['modulo_fiscal']) & (df['area'] <= 15 * df['modulo_fiscal']),
        (df['area'] > 15 * df['modulo_fiscal'])
    ]
    categorias = ['Minifúndio', 'Pequena Propriedade', 'Média Propriedade', 'Grande Propriedade']
    df['categoria'] = np.select(condicoes, categorias, default='Desconhecido')

    # Agrupar e contar por região administrativa e categoria
    resultado = df.groupby(['regiao_administrativa', 'categoria']).size().unstack(fill_value=0)

    # Garantir a ordem correta das colunas
    ordem_colunas = ['Minifúndio', 'Pequena Propriedade', 'Média Propriedade', 'Grande Propriedade']
    for col in ordem_colunas:
        if col not in resultado.columns:
            resultado[col] = 0  # Adiciona a coluna se não existir (pode acontecer em regiões sem uma das categorias)

    resultado = resultado[ordem_colunas]

    # Adiciona a coluna de total por região
    resultado['Total de Propriedades'] = resultado.sum(axis=1)

    return resultado


df_contagem = contar_propriedades_por_regiao(data)
display(df_contagem)

def preparar_dataframe_classificado(data):
    """
    Prepara um DataFrame contendo apenas as colunas relevantes e adiciona
    a coluna 'tipo_propriedade' com a classificação da propriedade com base
    na área e no módulo fiscal.

    Retorna colunas:
    ['lote_id', 'nome_municipio', 'distrito', 'numero_incra', 'area.1',
     'label_nome_municipio', 'regiao_administrativa', 'modulo_fiscal', 'tipo_propriedade']
    """

    # Filtrar apenas as colunas necessárias
    colunas_desejadas = [
        'lote_id',
        'nome_municipio',
        'distrito',
        'numero_incra',
        'area.1',
        #'label_nome_municipio',
        'regiao_administrativa',
        'modulo_fiscal',
        'area'
    ]
    df = data[colunas_desejadas].copy()

    # Remover registros com dados insuficientes para a classificação
    df = df.dropna(subset=['area', 'modulo_fiscal'])
    df = df[(df['area'] > 0) & (df['modulo_fiscal'] > 0)]

    # Classificar propriedades
    condicoes = [
        (df['area'] < 1 * df['modulo_fiscal']),
        (df['area'] >= 1 * df['modulo_fiscal']) & (df['area'] <= 4 * df['modulo_fiscal']),
        (df['area'] > 4 * df['modulo_fiscal']) & (df['area'] <= 15 * df['modulo_fiscal']),
        (df['area'] > 15 * df['modulo_fiscal'])
    ]
    categorias = ['Minifúndio', 'Pequena Propriedade', 'Média Propriedade', 'Grande Propriedade']
    df['tipo_propriedade'] = np.select(condicoes, categorias, default='Desconhecido')

    # Colunas finais
    colunas_finais = [
        'lote_id',
        'nome_municipio',
        'distrito',
        'numero_incra',
        'area.1',
        #'label_nome_municipio',
        'regiao_administrativa',
        'modulo_fiscal',
        'tipo_propriedade'
    ]

    return df[colunas_finais]

df_classificado = preparar_dataframe_classificado(data)
display(df_classificado)

def plot_barras_empilhadas_percentual(df_contagem):
    """
    Plota um gráfico de barras horizontais empilhadas com os percentuais
    de cada tipo de propriedade por região administrativa, com os valores
    percentuais visíveis sobre cada segmento da barra.
    """

    # Calcular percentuais
    df_percentual = df_contagem.div(df_contagem.sum(axis=1), axis=0) * 100
    df_percentual = df_percentual.sort_values(by="Minifúndio", ascending=False)

    # Paleta de cores
    cores = {
        "Minifúndio": "#9b19f5",
        "Pequena Propriedade": "#0040bf",
        "Média Propriedade": "#e6d800",
        "Grande Propriedade": "#d97f00"
    }

    fig, ax = plt.subplots(figsize=(14, 8))
    bottom = np.zeros(len(df_percentual))
    y_labels = df_percentual.index

    for categoria in ["Minifúndio", "Pequena Propriedade", "Média Propriedade", "Grande Propriedade"]:
        valores = df_percentual[categoria]
        bars = ax.barh(y_labels, valores, left=bottom, label=categoria, color=cores[categoria])

        # Adiciona os rótulos com percentuais
        for i, (valor, base) in enumerate(zip(valores, bottom)):
            if valor > 1:  # Evita poluição visual com valores muito pequenos
                ax.text(base + valor / 2, i, f'{valor:.1f}%', ha='center', va='center', fontsize=9, color='white')

        bottom += valores

    ax.set_xlabel("Percentual (%)")
    ax.set_title("Distribuição Percentual dos Tipos de Propriedade por Região Administrativa")
    ax.legend(title="Tipo de Propriedade", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()

plot_barras_empilhadas_percentual(df_contagem)