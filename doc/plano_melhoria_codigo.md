# Plano de melhoria do código do dashboard_fundiario_ceara

- **Data da análise:** 29/09/2026. Decisões do usuário registradas na mesma data.
- **Testes antes:** 143 passed, 1 xfailed, 220 avisos
- **Testes na 1.2.0:** dashboard 291 e miniserver 112, sem avisos
- **pyflakes:** 18 avisos
- **app.py:** 1422 linhas, 713 comentadas
- **Ambiente:** Python 3.13.11, Streamlit 1.59.2, folium 0.20.0, pandas 3.0.3, geopandas 1.1.4

Cada achado tem `arquivo:linha` conferido no código. **[reproduzido]** indica que o defeito foi executado e falhou de fato. **[provável]** depende de dados reais para confirmação.

## Ação urgente

A versão 1.2.0 do miniserver e do dashboard está publicada no Docker Hub e testada com os dados reais. Ela corrige a duplicação de assentamentos, reservatórios e regiões a cada reinício do miniserver (B10). Falta implantar as duas juntas pela stack atualizada. As tags antigas ainda contêm o `JWT_SECRET` e a senha do Postgres: a rotação (T0.4) continua pendente.

## Decisões registradas

| ID | Decisão |
|---|---|
| D-1 | Rotação anual do `JWT_SECRET` e da senha do Postgres, junto com a remoção das tags antigas no Docker Hub. Como os valores atuais estão expostos nas imagens, a primeira rotação é recomendada logo após T0.3; o ciclo anual conta a partir dela. |
| D-3 | Os arquivos sem uso foram movidos para `dashboard_fundiario_ceara/arquivos-sem-uso/`, ignorada pelo Git e pelo build da imagem. O `LEIAME.md` da pasta explica cada arquivo. Aguardando sua revisão (T1.4). |
| D-4 | Convenção de nomes camelCase, com identificadores em português e sem acentos. Detalhes abaixo. Já registrada nas definições dos agentes do dashboard. |
| D-5 | O nome do proprietário só aparece quando a LGPD permite. Pessoa física fica oculta como "Pessoa física (protegido pela LGPD)". Aparece só o nome que identifica com segurança pessoa jurídica ou ente público: termina em LTDA ou S/A, ou traz termo institucional como associação, cooperativa ou prefeitura. Espólio e empresário individual (ME, MEI, EIRELI) ficam ocultos. A regra é conservadora e merece revisão jurídica do IDACE. |
| D-6 | Os dados são atualizados uma vez por mês. O cache do dashboard passa a ter TTL de 24 horas, para que a carga mensal apareça no máximo um dia depois. A atualização depende de resolver a comunicação com a GeoAPI do IDACE (Trilha G). |
| D-8 | Em 29/09, as tarefas que exigiam container novo do MiniServer ficaram para depois. Em 30/09 foram feitas na versão 1.2.0 do miniserver e do dashboard: importador da GeoAPI, versão dos dados, nomes fora da API e validação de `aud` e `iss` no JWT. |
| D-9 | A convenção camelCase vale para o dashboard. O miniserver mantém o snake_case que já usa, até decisão sua. |

### Convenção de nomes (D-4)

- Funções, métodos, variáveis e parâmetros em lowerCamelCase: `carregarLotes`, `adicionarCamadaMunicipios`.
- Classes em UpperCamelCase: `ErroApi`, `Pagina`.
- Constantes de módulo em MAIUSCULAS_COM_SUBLINHADO: `CENTRO_CEARA`, `ZOOM_PADRAO`.
- Módulos novos em lowerCamelCase: `apiCliente.py`, `camadasMapa.py`. Os módulos atuais são renomeados na Fase 6.
- Helpers privados com prefixo `_` seguido de camelCase: `_normalizarTexto`.
- Exceções: APIs de bibliotecas externas, colunas de DataFrame e chaves JSON vindas do miniserver (contrato de dados, como `nome_municipio`) e o prefixo `test_` exigido pelo pytest.
- A PEP 8 recomenda snake_case em Python. O ruff será configurado para não cobrar isso, e um teste garante o camelCase (T6.4).

---

## 1. Achados

### 1.1 Segurança

| ID | Severidade | Achado | Onde | Situação |
|---|---|---|---|---|
| S1 | Crítico | A imagem publicada contém `.streamlit/secrets.toml` com o `JWT_SECRET` real, idêntico ao arquivo local. A tag `1.1.0` também contém o `.env` com `POSTGRES_USER` e `POSTGRES_PASSWORD`. O `.dockerignore` não exclui `secrets.toml`, e o `COPY . .` leva o arquivo para a imagem. O repositório no Docker Hub responde 404 para acesso anônimo e parece privado, mas qualquer conta ou máquina com permissão de pull obtém o segredo. | `.dockerignore`, `Dockerfile.dfundce:36`, tags `1.1.0` e `1.1.1` | parcial: O código já deixa o secrets.toml fora da próxima imagem. Faltam T0.3 e T0.4. |
| S1a | Crítico | A produção depende desse arquivo embutido. O serviço `dfundce` em `docker-compose.stack.yml` não define `JWT_SECRET` nem monta `secrets.toml`, e o código só lê `st.secrets`. Corrigir apenas o `.dockerignore` derruba a autenticação com o miniserver. A Fase 0 define a ordem segura. | `data_loader.py:16`, `mapa_assentamento.py:17`, `mapa_escolas.py:75`, `mapa_reservatorios.py:39` | corrigido: O segredo vem do ambiente e a stack já passa JWT_SECRET ao dfundce. |
| S2 | Alto | Injeção de HTML: valores vindos da API entram em HTML sem escape. Um nome de assentamento, reservatório ou município malformado executa JavaScript no iframe do mapa. | `mapa_assentamento.py:178-187`, `mapa_reservatorios.py:261-271`, `mapa_gini.py:179`, `mapa_gini.py:263` | corrigido |
| S3 | Médio | Dados pessoais e LGPD: `nome_proprietario` aparece no tooltip da Malha Fundiária e vai embutido no HTML do mapa. Todos os nomes de proprietários de uma região chegam ao navegador. A decisão é do IDACE. | `mapa_interativo.py:312`, `data_loader.py:110` | corrigido: Desde a 1.2.0 a API também entrega o nome protegido e um pseudônimo. |
| S4 | Médio | JavaScript injetado no documento pai via `components.html` para colorir os botões do menu. Depende de iframe same-origin e cria 9 iframes a cada interação. | `app.py:595-614` | corrigido |
| S5 | Médio | O `config.toml` de produção tem `enableXsrfProtection = false`, `enableCORS = false`, `runOnSave = true` e `fileWatcherType = "auto"`. A opção `server.maxCacheSize` não existe e gera aviso na inicialização. | `.streamlit/config.toml` | parcial: Falta testar XSRF atrás do proxy. |
| S6 | Baixo | Mensagens de erro exibem a URL interna do miniserver e a exceção crua ao usuário final. | `data_loader.py:68,121,154,197`, `mapa_assentamento.py:78`, `mapa_interativo.py:263` | corrigido |
| S7 | Baixo | O container roda como `root` e não tem `HEALTHCHECK`. A base `python:3.13-slim-bullseye` usa Debian 11, cujo LTS terminou em agosto de 2026. Nenhuma dependência tem versão fixada. | `Dockerfile.dfundce`, `requirements.txt` | corrigido |
| S8 | Baixo | Imagens carregadas de `i.imgur.com` e `idace.ce.gov.br`: o terceiro recebe o IP de cada visitante e a página quebra se o link sair do ar. | `app.py:135,256,259,304`, `style.css:690-750,1135-1141` | pendente: Aguarda T7.7. |
| S9 | Baixo | O JWT usa `datetime.utcnow()`, que está depreciado, é assinado a cada requisição e não tem `aud` nem `iss`. O segredo é lido na importação; sem ele, o app quebra com um `KeyError` pouco claro. | os quatro módulos de S1a | corrigido: O miniserver 1.2.0 exige aud e iss; dashboard e Terra-AI enviam. |

Fora do escopo do dashboard, para o integration-tester e o miniserver-code-analyst: o miniserver publica a porta 8000 no host e usa `allow_origins=["*"]` (`terraGeoDataMiniServer/data_service/main.py:75`). O `docker-compose.yml` do dashboard publica o Postgres na porta 5432 e usa `postgis:latest`.

### 1.2 Bugs

| ID | Severidade | Achado | Onde | Situação |
|---|---|---|---|---|
| B1 | Alto | **[reproduzido]** Escolas do Campo: ao selecionar "mons. Tabosa", o filtro compara com `sel.lower()`, a lista fica vazia e a página quebra com `KeyError: 'por_crede'`. Os nomes de município nesses dados misturam formatos. A coordenada da EEM Florestan Fernandes cai em Fortaleza, não em Monsenhor Tabosa. | `mapa_escolas.py:39,63-65,303-315,339,356` | corrigido |
| B2 | Alto | **[reproduzido]** Mapa de Predominância: se algum município do contorno não tiver lotes, o seletor de município faz `.iloc[0]` numa seleção vazia e a página quebra com `IndexError`. | `mapa_predominancia.py:257,271` | corrigido |
| B7 | Alto | Os dados só se atualizam quando o container reinicia. `load_once` é `cache_resource` sem TTL e envolve todas as cargas, então os TTLs internos nunca têm efeito. Isso impede a atualização mensal decidida. | `app.py:73-76` | corrigido |
| B5 | Médio | Quando o filtro deixa um tipo de assentamento vazio, o tooltip do grupo vazio lança `AssertionError`. Já documentado num teste `xfail`. A cópia em `mapa_escolas.py` tem o mesmo defeito. | `mapa_reservatorios.py:138-213`, `mapa_escolas.py:162-237`, `tests/test_mapa_reservatorios.py:73` | corrigido |
| B6 | Médio | **[provável]** Mapa de Gini: o clique lê o texto do tooltip, pega o nome original do município e compara com o nome normalizado. Os formatos diferem, então o Gini do município clicado provavelmente nunca aparece. | `mapa_gini.py:166,255-262` | corrigido |
| B8 | Médio | `cache_resource` devolve o mesmo DataFrame para todas as sessões, e uma mutação numa sessão vaza para as outras. Funções já decoradas em `data_loader` são decoradas de novo no `app.py`. | `app.py:55-61`, `data_loader.py:135,157`, `mapa_predominancia.py:85` | corrigido |
| B9 | Médio | Defaults de URL divergentes: `data_loader` usa `http://localhost:8000` e os outros três módulos terminam em `/api`, prefixo que o miniserver não tem. Sem `DATA_SERVICE_URL` no ambiente, três páginas recebem 404. O `conftest.py` remove o `/api` e esconde o problema. | `data_loader.py:30`, `mapa_assentamento.py:30`, `mapa_escolas.py:87`, `mapa_reservatorios.py:51`, `tests/conftest.py:141-143` | corrigido |
| B10 | Crítico | **[reproduzido]** A cada reinício do container do miniserver, a carga dos CSVs inseria de novo assentamentos, reservatórios e regiões sem apagar a carga anterior. Duas cargas seguidas levaram assentamentos de 454 para 908, reservatórios de 157 para 314 e regiões de 184 para 368. Em produção, os mapas podem estar mostrando cada item repetido. A malha fundiária mantinha para sempre imóveis que saíram da fonte. | `terraGeoDataMiniServer/importer_all.py` | corrigido |
| B3 | Baixo | Valor padrão `modo_mapa="_categorias Dominantes"`, resto de um localizar e substituir. Não se manifesta hoje porque o chamador sempre passa o valor. | `mapa_predominancia.py:90` | corrigido |
| B4 | Baixo | **[reproduzido]** `adicionar_camada_assentamentos` usa `COR_ASSENTAMENTO`, que não existe, e lança `NameError`. A função só é chamada em comentário. | `mapa_reservatorios.py:281-308` | corrigido |

### 1.3 Redundância de código

| Item duplicado | Cópias | Onde |
|---|---|---|
| `create_jwt_token` com `JWT_SECRET` e `JWT_ALGORITHM` | 4 | `data_loader.py:16-27`, `mapa_assentamento.py:17-27`, `mapa_escolas.py:75-85`, `mapa_reservatorios.py:39-48` |
| `DATA_SERVICE_URL` e `REQUEST_TIMEOUT` | 4, mais 1 sem uso | mesmos módulos, com defaults divergentes, e `app.py:40` |
| `_fetch_from_api` idêntica | 3 | `data_loader.py:34`, `mapa_escolas.py:93`, `mapa_reservatorios.py:57` |
| `carregar_municipios` e `carregar_assentamentos` | 2 cada | `mapa_escolas.py:131-136`, `mapa_reservatorios.py:99-104` |
| `adicionar_camada_municipios` | 2, mais 1 comentada | `mapa_escolas.py:271`, `mapa_reservatorios.py:311` e `343-387` |
| `adicionar_camadas_assentamentos` | 2, mais 1 variante | `mapa_escolas.py:162`, `mapa_reservatorios.py:138`, `mapa_assentamento.py:90` |
| `formatar_valor` | 3 | `mapa_assentamento.py:52`, `mapa_escolas.py:146`, `mapa_reservatorios.py:122` |
| `criar_mapa_base` | 3 | `mapa_assentamento.py:81`, `mapa_escolas.py:154`, `mapa_reservatorios.py:130` |
| `CENTRO_CEARA` e `ZOOM_PADRAO` | 3, mais 3 centros literais diferentes | os três módulos acima, `mapa_interativo.py:213`, `mapa_gini.py:159`, `mapa_predominancia.py:104` |
| `CORES_ASSENTAMENTOS` | 3, mais `CORES_MARKERS` idêntico | `mapa_assentamento.py:34-42`, `mapa_escolas.py:25`, `mapa_reservatorios.py:25` |
| Classificação por módulo fiscal | 3 | `data_loader.py:166-178`, `grafico_interativo.py:33-47` e `158-168` |
| `color_map`, cópia de `CORES` | 3 | `grafico_interativo.py:57,103,177` |
| Funções `fetch_*` que refazem token e requisição | 5 | `data_loader.py:201-247` |
| `DebugInfo` | 2 | `app.py:15`, `mapa_predominancia.py:15` |
| Controles de mapa e blocos HTML de texto | 6 páginas, cerca de 15 blocos | todas as páginas |

Acoplamento indevido: `mapa_gini`, `mapa_predominancia` e `mapa_assentamento` importam helpers de `mapa_reservatorios`, que é uma página. Helpers compartilhados precisam de um módulo próprio. O `df_class` já chega com a coluna `categoria`, e mesmo assim os gráficos recalculam a classificação.

### 1.4 Redundância de chamadas à API

| ID | Severidade | Achado | Onde | Situação |
|---|---|---|---|---|
| R1 | Alto | `load_municipios` faz 185 requisições sequenciais: a lista e um `geojson_muni` para cada um dos 184 municípios. O mesmo endpoint com `municipio=todos` devolve tudo numa chamada. Roda no topo do `app.py`, então até a página inicial espera na primeira visita após o deploy. | `data_loader.py:136-145`, `app.py:91` | corrigido |
| R6 | Alto | Assentamentos sem cache: o GeoJSON inteiro é baixado de novo a cada interação com qualquer controle da página. Assentamentos são buscados por três funções diferentes. | `mapa_assentamento.py:65,226`, `mapa_escolas.py:131`, `mapa_reservatorios.py:99` | corrigido |
| R2 | Médio | Os mesmos polígonos de município são buscados por quatro funções com caches separados e ainda copiados para `st.session_state.geo_muni` em cada sessão. | `data_loader.py:125,237`, `mapa_escolas.py:135,361`, `mapa_reservatorios.py:103,442`, `mapa_gini.py:161`, `mapa_predominancia.py:109`, `mapa_assentamento.py:337` | corrigido |
| R5 | Médio | Malha Fundiária com a opção "(toda a região)": uma requisição de limites por município da região, quando bastaria filtrar o GeoJSON de todos os municípios já em cache. | `mapa_interativo.py:254-257` | corrigido |
| R9 | Médio | Sem `requests.Session`: cada requisição abre uma conexão nova, o que agrava R1. O token é assinado de novo a cada chamada. | todos os módulos que usam `requests.get` | corrigido |
| R3 | Baixo | `validate_data` chama `/version`, que não existe no miniserver e sempre devolve 404. O resultado vai para `counts`, que nunca é usado. | `data_loader.py:185`, `app.py:89` | corrigido |
| R4 | Baixo | `/regioes` é buscado duas vezes, com caches diferentes. | `data_loader.py:98,202` | corrigido |
| R7 | Baixo | Contador `api_calls` dentro de função cacheada: só conta quando o cache falha e nunca é lido. | `data_loader.py:37-38`, `mapa_escolas.py:96-97`, `mapa_reservatorios.py:60-61` | corrigido |
| R8 | Baixo | Fallback para `backup/{endpoint}.json`, pasta que não existe. São três cópias de um caminho morto. | `data_loader.py:65`, `mapa_escolas.py:124`, `mapa_reservatorios.py:88` | corrigido |

### 1.5 Código comentado e não usado

**Blocos comentados**

- `app.py:710-1422`: cópia integral do próprio arquivo, comentada. São 713 linhas, metade do arquivo.
- `mapa_interativo.py:1-152`: versão antiga da página inteira.
- Blocos menores: `app.py:10,12,37,235-245,252,532-533,643-647`; `grafico_interativo.py:320,363-369,372`; `mapa_predominancia.py:151-159,214-226,261`; `mapa_reservatorios.py:24,343-387,448`; `mapa_assentamento.py:73-74,233`; `public/cores.py:19-25`.

**Código sem uso**

- `app.py`: import `st_folium` (9), `DebugInfo` (15-18), `load_municipios` importado duas vezes (23, 25), `REQUEST_TIMEOUT` (40), docstring depois do `return` (78-86), `df_inter` sempre `None`, `df_ctx` e `counts` (89), `col1` a `col4` (230).
- `grafico_interativo.py`: `legenda` (136), `df_original` (332), `plot_cadastro_pizza_estilo_original` (236-310, só referenciada em comentário), `selected_tab` definido duas vezes e nunca lido (315-316, 335-336). A docstring cita `compute_stats_df`, que não existe.
- `mapa_gini.py`: `import os` (15), `valor_str` (106), `warning_munis` sem uso (83-86), `df_no` calculado e descartado (54-79), parâmetro `clicou` sobrescrito (206, 231) e retorno ignorado.
- `mapa_assentamento.py`: `cor_marker` (191) e um `print()` em produção (214).
- `mapa_escolas.py`: imports `shape`, `List`, `pd` e `Optional` duplicado (10-14).
- `mapa_reservatorios.py`: `List` e `Optional` duplicado (11), função quebrada de B4 (281-308), `except: pass` sem tipo (396, 398).
- `mapa_predominancia.py`: bloco de debug desligado por `show_debug_info = False` (289-315).
- `data_loader.py`: parâmetro `base_folder` sem uso (94, 136), contador `api_calls` e fallback `backup/`.
- `modules/__init__.py` exporta helpers que ninguém importa de fora: `filtrar_dados`, `classificar_propriedades`, `plot_*`, `preparar_dados`, `criar_mapa_contextual`.
- f-strings sem placeholder: `mapa_assentamento.py:290`, `mapa_escolas.py:330`, `mapa_reservatorios.py:419`.

**Arquivos sem uso, já movidos para arquivos-sem-uso/**

- `test_app.py`, `para-podman.txt` e `.gitignore.orig`, da raiz.
- `util/create_shapefile.py` e `util/screenshot.py`, que usam `../data` e `selenium`, fora do `requirements.txt`.
- `removed_registers/gini_removed_2025-06-26.csv`, que só tem o cabeçalho.
- Seis imagens de `assets/`: duas sem nenhuma referência e quatro referenciadas só em código comentado da página Sobre.

### 1.6 Despadronização de nomes

- Idiomas misturados: `load_csv_data`, `load_municipios`, `validate_data`, `fetch_regioes` e `fetch_geojson_*` em inglês convivem com `carregar_*`, `obter_*`, `adicionar_*` e `preparar_dados` em português. As páginas se chamam `render_view_*`, mas há `render_map`, `style_fn` e `calc_gini_df`.
- Mesmo conceito com nomes e tipos diferentes: `load_municipios` devolve GeoDataFrame, `carregar_municipios` e `fetch_geojson_limites` devolvem dict, `obter_municipios` e `fetch_municipios` devolvem listas de nomes.
- Nomes enganosos: `load_csv_data` não lê CSV, lê a API. `validate_data` não valida, classifica. O `app.py` ainda a renomeia para `load_data`.
- Estilos misturados no mesmo arquivo: `ChangeButtonColour` e `ChkBtnStatusAndAssignColour` em PascalCase, `mapa_de_Predominância`, `mapa_Assentamentos` e `mapa_hidrográfico` com maiúscula no meio e acento, constantes em minúsculas como `tolerancia` e `pressed_colour`, e "colour" britânico ao lado de "cor".
- Chaves de página diferentes dos rótulos e dos módulos: "Mapa Hidrografico" sem acento, rótulo "Mapa Hidrográfico", módulo `mapa_reservatorios`. O mesmo ocorre com Assentamento e Assentamentos, Gráficos e Gráficos e Quadros, Malha Fundiária e `mapa_interativo`, Concentração Fundiária e `mapa_gini`.
- Nomes curtos demais: `m`, `c`, `g`, `p`, `co2_1`, `co2_2`, `sel`, `tbl`. Alias `mystate` para `st.session_state`.
- Prefixo `_` para o Streamlit não hashear parâmetros usado de forma inconsistente: `_muni_gdf` tem, `df_ctx`, o maior deles, não tem.

A convenção adotada para corrigir isso está em D-4.

### 1.7 Bibliotecas

- Importadas e não usadas: `st_folium` no `app.py`; `shape`, `List` e `pandas` em `mapa_escolas.py`; `os` em `mapa_gini.py`; `List` em `mapa_reservatorios.py`.
- As 10 bibliotecas do `requirements.txt` são usadas.
- Usada e não declarada: `branca`, em `mapa_predominancia.py:5`, que só chega como dependência do folium.
- Instaladas na imagem sem uso: `gunicorn`, porque o entrypoint é `streamlit run`, e `python3-gdal`, que atende o Python do sistema e não o 3.13 da imagem. `gdal-bin` e `libgdal-dev` provavelmente também sobram, porque o geopandas 1.x usa wheels com GDAL embutido.
- Nenhuma versão fixada. O venv já está em pandas 3.0 e Streamlit 1.59, e um rebuild pode trazer versões incompatíveis.
- APIs depreciadas: `use_container_width`, a trocar por `width="stretch"`, e `datetime.utcnow()`.
- Versões de Python divergentes: 3.13.9 em `.python-version`, 3.13.3 em `.tool-versions` e `3.13-slim-bullseye` no Dockerfile.

### 1.8 Desempenho de renderização

| ID | Severidade | Achado | Onde | Situação |
|---|---|---|---|---|
| D1 | Alto | Carga global no topo do `app.py`: toda página, inclusive Início e Sobre, depende da carga completa dos lotes e das 185 requisições de limites de R1. | `app.py:89-91` | corrigido |
| D3 | Alto | Gini: outliers recalculados a cada rerun sem cache, `df_no` calculado e descartado, normalização linha a linha com `.apply` e `iterrows` para 184 rótulos. Cada clique no mapa e cada troca de região reconstroem o mapa inteiro. | `mapa_gini.py:57-58,173-180,208-217` | corrigido |
| D4 | Alto | Assentamentos: um GeoJSON, um tooltip e um marcador por feição. O HTML cresce linearmente com objetos duplicados e o navegador fica lento. | `mapa_assentamento.py:131-212` | corrigido |
| D2 | Médio | DataFrames grandes são hasheados a cada rerun pelos decoradores de cache. Em cada interação, o conjunto de lotes do estado inteiro é hasheado várias vezes. | `mapa_gini.py:44`, `grafico_interativo.py:21,32,152`, `mapa_predominancia.py:85` | corrigido |
| D5 | Médio | Predominância: polígonos dos municípios desenhados três vezes no modo coroplético e duas no modo de calor. O mapa de calor usa `iterrows` e centróide em coordenadas geográficas. O mapa ignora o basemap do projeto. | `mapa_predominancia.py:103-165` | corrigido |
| D6 | Médio | Malha Fundiária: GeoJSON convertido em GeoDataFrame e de volta em JSON duas vezes, com simplificação no cliente, embora o endpoint aceite `tolerance` e simplifique no PostGIS. | `mapa_interativo.py:171-202,271-274` | corrigido |
| D7 | Médio | Figuras matplotlib cacheadas e nunca fechadas. Cada nova combinação de filtros abre três figuras que ficam na memória do processo. | `grafico_interativo.py:51-310` | corrigido |
| D8 | Médio | Barra lateral: nove iframes recriados a cada interação, em qualquer página. | `app.py:609,640` | corrigido |
| D9 | Médio | GeoJSON grande copiado para o `session_state` de cada sessão. A memória do servidor cresce com o número de usuários simultâneos. | ver R2 | corrigido |
| D10 | Baixo | `style.css`, com 30 KB, lido do disco e reenviado a cada rerun. | `app.py:522-523` | corrigido |

---

## 2. Plano de execução por agentes

### 2.1 Regras para todos os agentes

1. Rodar `.venv/bin/python -m pytest -q` em `dashboard_fundiario_ceara/` antes e depois de cada tarefa e relatar o resultado real.
2. Para bugs, o dashboard-tester escreve primeiro o teste que falha e o dashboard-implementer corrige até ficar verde.
3. Uma tarefa por vez em cada arquivo. Tarefas em paralelo usam worktree isolada.
4. Nenhum agente rotaciona segredos, faz push ou cria commit sem pedido explícito. Commits seguem o estilo curto do projeto.
5. Todo código novo, desde a Fase 0, segue a convenção camelCase. O legado só é renomeado na Fase 6, exceto o trecho que a própria tarefa reescreve.
6. A partir da Fase 3, nenhuma chamada `st.*` dentro de função cacheada.
7. O dashboard-code-analyst revalida os critérios de aceite no fim de cada fase.

### Fase 0: Contenção de segredos

A ordem importa. A produção lê o `JWT_SECRET` do arquivo embutido na imagem. Excluir o arquivo antes de a variável existir na stack derruba o dashboard. Política decidida: rotação anual dos segredos junto com a remoção das tags antigas.

| ID | Executor | Status | Tarefa | Aceite |
|---|---|---|---|---|
| T0.1 | dashboard-implementer | feita | Criar `modules/config.py` com `JWT_SECRET`, `DATA_SERVICE_URL` com default `http://localhost:8000` sem `/api`, e `REQUEST_TIMEOUT`. Ler `JWT_SECRET` da variável de ambiente capturada na importação, com fallback para `st.secrets`, no mesmo padrão de `modules/basemap.py`, porque o Streamlit copia o `secrets.toml` para `os.environ`. Sem segredo, lançar erro com mensagem clara. Os quatro módulos passam a importar dali, sem outra refatoração. | pytest verde. Teste novo: a variável de ambiente tem precedência. Teste novo: a ausência do segredo gera erro legível. |
| T0.2 | dashboard-implementer | feita | Adicionar `.streamlit/secrets.toml`, `.env`, `tests/`, `doc/` e `scripts/` ao `.dockerignore`, com teste em `tests/test_higieneRepositorio.py`. O `publish-docker.sh` agora pede confirmação de T0.3 antes de publicar. Feito em 29/09. | Build local e `test ! -f .streamlit/secrets.toml` dentro da imagem. |
| T0.3 | Humano | pendente | Reimplantar a stack no Portainer com o `docker-compose.stack.yml` atualizado, que passa ao `dfundce` a mesma `JWT_SECRET` do `tgdmserver`. Com a imagem atual isso é inofensivo. Depois, publicar a imagem nova com `./publish-docker.sh` e validar. Passo a passo em `doc/rotacao_segredos.md`. | Todas as páginas carregam dados em produção. |
| T0.4 | Humano | pendente | Primeira rotação, recomendada logo após T0.3: trocar o `JWT_SECRET` no dashboard e no miniserver, trocar a senha do Postgres e apagar as tags `1.1.0`, `1.1.1` e o `latest` antigo no Docker Hub. Revisar quem tem permissão de pull. | Tags antigas removidas e segredos novos em uso. |
| T0.5 | integration-tester | pendente | Validar ponta a ponta o JWT com o segredo novo e o `DATA_SERVICE_URL` sem `/api`. | Cada endpoint usado pelo dashboard responde 200. |
| T0.6 | dashboard-implementer | feita | Escrever `doc/rotacao_segredos.md` com o procedimento anual: gerar os segredos, atualizar as duas stacks no Portainer, publicar imagens novas, apagar as tags antigas e validar. | Procedimento revisado por você. |
| T0.7 | Humano | pendente | Rotação anual seguindo `doc/rotacao_segredos.md`, um ano depois de T0.4 e a cada ano a seguir. | Data da rotação registrada. |

### Fase 1: Limpeza de código morto

Baixo risco. Vem antes dos bugs porque reduz o tamanho dos diffs das fases seguintes.

| ID | Executor | Status | Tarefa | Aceite |
|---|---|---|---|---|
| T1.1 | dashboard-implementer | feita | Remover os blocos comentados listados em Código morto. O gráfico de Geocadastro foi mantido como `plotarSituacaoCadastro`, sem uso, até a decisão D-2. Feito em 29/09. | `app.py` abaixo de 720 linhas e pytest verde. |
| T1.2 | dashboard-implementer | feita | Remover imports, variáveis e funções sem uso: `DebugInfo` nos dois lugares, o bloco de debug da predominância, `api_calls`, o fallback `backup/`, a chamada a `/version` com `counts`, `df_inter`, a função quebrada de B4, o `print`, os `except:` sem tipo e as f-strings sem placeholder. | `pyflakes app.py modules/` sem avisos e pytest verde. |
| T1.3 | dashboard-tester | feita | Adicionar o `ruff` ao `requirements-dev.txt`, com as regras `F`, `E9` e `B` num `ruff.toml` mínimo. | `ruff check` sem erros. |
| T1.4 | Humano | parcial | Revisar `arquivos-sem-uso/`, cujo `LEIAME.md` explica cada arquivo. Devolver o que ainda servir e apagar o resto. Doze arquivos movidos em 29/09; as remoções aparecem no `git status` do dashboard. | Pasta revisada. |

### Fase 2: Bugs e segurança no código

Cada bug começa com um teste que falha.

| ID | Executor | Status | Tarefa | Aceite |
|---|---|---|---|---|
| T2.1 | dashboard-tester + dashboard-implementer | feita | B1: normalizar os nomes de `ESCOLAS_DO_CAMPO` no formato de `nome_municipio` e fazer as estatísticas sempre devolverem a contagem por CREDE. Conferir com você a coordenada da EEM Florestan Fernandes. | Um teste que seleciona cada município da lista passa. |
| T2.2 | dashboard-tester + dashboard-implementer | feita | B2: o seletor e a tabela de município tratam município sem lotes. | O cenário reproduzido renderiza sem exceção. |
| T2.3 | dashboard-implementer | feita | B3: corrigir o valor padrão de `modo_mapa`. | Teste de assinatura. |
| T2.4 | dashboard-tester + dashboard-implementer | feita | B5: pular grupos de assentamento vazios. | O teste `xfail` passa e a marcação é removida. |
| T2.5 | integration-tester + dashboard-implementer | feita | B6: confirmar com dados reais os formatos de `nome_municipio` e `nome_municipio_original`. Trocar a leitura do texto do tooltip por `returned_objects=["last_active_drawing"]`, lendo as propriedades da feição. | Clicar num município mostra o Gini dele, com teste que simula o retorno do mapa. |
| T2.6 | dashboard-implementer | feita | S2: aplicar `html.escape` a todo valor de dado interpolado em HTML. Verificar se o tooltip de GeoJSON do folium já escapa os valores. | Um nome com `<script>` aparece como texto literal. |
| T2.7 | dashboard-implementer | feita | S6: mensagem genérica ao usuário e o detalhe no `logging`. | Nenhuma URL interna em `st.error`. |
| T2.8 | dashboard-implementer | feita | B7 e B8, conforme D-6: sem `load_once` e sem decorador duplicado. Todo cache expira em 24 horas. Os DataFrames grandes ficam em `cache_resource`, tratados como somente leitura, porque copiar dezenas de milhares de linhas a cada interação custaria mais que o risco que B8 descrevia. | Teste: depois do TTL, a carga busca a API de novo. |

### Fase 3: Camada única de acesso à API

Meta: a primeira carga cai de cerca de 187 requisições, mais uma por região, para cerca de 3, mais uma por região.

| ID | Executor | Status | Tarefa | Aceite |
|---|---|---|---|---|
| T3.1 | dashboard-implementer | feita | Criar `modules/apiCliente.py` com `requests.Session` reaproveitada, token reaproveitado até perto do vencimento, datas em UTC com fuso, uma função `buscarJson(endpoint, parametros)` que lança `ErroApi` e nenhuma chamada `st.*`. | Testes do cliente com `requests_mock`. |
| T3.2 | dashboard-implementer | feita | Criar `modules/repositorio.py` com uma função cacheada por endpoint: `carregarRegioes`, `carregarMunicipiosDaRegiao`, `carregarLimitesMunicipais` com uma única chamada `municipio=todos`, `carregarLotesDaRegiao`, `carregarGeojsonLotes` com tolerância, `carregarAssentamentos`, `carregarMunicipiosComAssentamento`, `carregarReservatorios` e `carregarMunicipiosComReservatorio`. | Cada endpoint aparece em uma única função. |
| T3.3 | dashboard-implementer | feita | Migrar todas as páginas para o repositório. Tirar `geo_muni` e `geo_assent` do `session_state`. Na Malha Fundiária, filtrar os limites da região a partir do GeoJSON de todos os municípios. Apagar as cópias de `_fetch_from_api` e `create_jwt_token`. | Nenhuma duplicata por grep e pytest verde. |
| T3.4 | dashboard-tester | feita | Testes de contagem de requisições: limites municipais em uma chamada, primeira carga com no máximo 3 mais uma por região, nenhum endpoint repetido dentro do TTL. Tirar do `conftest.py` o tratamento de `/api`. | Testes novos verdes. |
| T3.5 | integration-tester | feita | Contrato validado contra o miniserver rodando localmente com os dados reais (233.366 imóveis). A geometria já vem em GeoJSON, o que dispensou `convert_hex_to_geojson`. Feito em 30/09. | Relatório de contrato. |

### Fase 4: Componentes compartilhados de mapa e interface

| ID | Executor | Status | Tarefa | Aceite |
|---|---|---|---|---|
| T4.1 | dashboard-implementer | feita | Criar `modules/constantes.py` com centro e zoom do Ceará, cores de assentamento, categorias fundiárias e tolerância de simplificação. | Nenhuma constante duplicada. |
| T4.2 | dashboard-implementer | feita | Criar `modules/camadasMapa.py` com `criarMapaBase`, `adicionarCamadaMunicipios`, `adicionarCamadasAssentamentos` com laço por tipo que pula grupo vazio, `adicionarControles` e `formatarValor`. Todas as páginas usam o basemap do projeto, inclusive Predominância e Malha Fundiária. | Nenhuma página importa de `mapa_reservatorios`. |
| T4.3 | dashboard-implementer | feita | Criar `modules/classificacao.py` com `classificarPorModuloFiscal`, única implementação das faixas de 1, 4 e 15 módulos fiscais. Os gráficos usam a coluna `categoria` já calculada. | Uma implementação só e teste nas fronteiras de 1, 4 e 15 MF. |
| T4.4 | dashboard-implementer | feita | Criar `modules/componentesUi.py` com `paragrafoInformativo(texto)` e `cabecalhoFiltros()` para substituir os blocos HTML repetidos. | Nenhum bloco HTML repetido nas páginas. |

### Fase 5: Desempenho de renderização

A linha de base é medida antes de qualquer otimização.

| ID | Executor | Status | Tarefa | Aceite |
|---|---|---|---|---|
| T5.0 | dashboard-tester | feita | Criar `tests/benchPaginas.py`, fora da execução padrão do pytest, com dados sintéticos de volume realista. Medir o tempo por página e o tamanho em bytes do HTML de cada mapa. Registrar a linha de base antes de T5.1. | Tabela de linha de base anexada ao plano. |
| T5.1 | dashboard-implementer | feita | D4: um GeoJSON por tipo de assentamento e marcadores com `FastMarkerCluster`, criados no navegador a partir de uma lista compacta. | HTML do mapa de assentamentos pelo menos 50% menor. |
| T5.2 | dashboard-implementer | feita | D5: polígonos municipais desenhados uma vez só. Centróides vetorizados na projeção métrica EPSG:31984, SIRGAS 2000 UTM 24S. | Uma única camada de polígonos municipais no HTML. |
| T5.3 | dashboard-implementer | feita | D3: tabela de Gini calculada uma vez por carga de dados, sem hashear DataFrames. Normalização de nomes vetorizada. Remover ou exibir `df_no`. Coluna da direita em `@st.fragment`, para que o filtro de região não reconstrua o mapa. | Trocar a região não reconstrói o mapa, medido no benchmark. |
| T5.4 | dashboard-implementer | feita | D6: pedir a simplificação ao servidor e converter a geometria uma única vez. | Uma conversão por renderização. |
| T5.5 | dashboard-implementer | feita | D7: cachear os dados agregados em vez das figuras e fechar cada figura depois de exibida. Avaliar gráficos nativos conforme D-7. | Número de figuras abertas estável após várias trocas de filtro. |
| T5.6 | dashboard-implementer | feita | D1 e D10: carregar lotes e limites só nas páginas que os usam e ler o CSS uma vez por processo. | Início e Sobre renderizam sem chamar a API. |
| T5.7 | dashboard-implementer | feita | D8 e S4: trocar `components.html` por CSS, usando as classes `st-key-` dos botões ou `type="primary"` no botão ativo. | Nenhum iframe na barra lateral. |

### Fase 6: Nomes em camelCase e navegação

Convenção decidida em D-4. O código novo das fases anteriores já nasce em camelCase; aqui o legado é renomeado.

| ID | Executor | Status | Tarefa | Aceite |
|---|---|---|---|---|
| T6.1 | Claude | feita | Registrar a convenção camelCase e a estrutura nova nas definições dos agentes do dashboard e do integration-tester. Feito em 29/09. | Os três arquivos em `.claude/agents/` contêm a seção Convenção de nomes. |
| T6.2 | dashboard-implementer | feita | Navegação dirigida por tabela: uma lista `PAGINAS` de objetos `Pagina` com chave, rótulo, ícone e função. Elimina a cadeia `if/elif`, o `[False] * 9`, o `st.title("").markdown` e as chaves divergentes. | `app.py` sem `if/elif` de páginas e smoke de todas as páginas verde. |
| T6.3 | dashboard-implementer + dashboard-tester | feita | Renomear o legado para camelCase e atualizar os testes no mesmo passo: `load_csv_data` vira `carregarLotes`, `validate_data` vira `classificarLotes`, `render_view_gini_map` vira `renderizarPaginaGini`, `get_carto_api_key` vira `obterChaveCarto`. Os módulos das páginas recebem o nome da página, como `paginaAssentamentos.py` e `paginaHidrografia.py`. | pytest verde. |
| T6.4 | dashboard-tester | feita | Garantir a convenção: ruff com pep8-naming ignorando as regras que exigem snake_case (N802, N803, N806, N815, N816, N999) e um teste que percorre `app.py` e `modules/` com `ast` e reprova nomes fora do padrão. Documentar a convenção no README do dashboard. | `ruff check` e o teste de convenção verdes. |

### Fase 7: Dependências, configuração e entrega

Mexe em arquivos de infraestrutura e pode rodar em paralelo à Fase 2.

| ID | Executor | Status | Tarefa | Aceite |
|---|---|---|---|---|
| T7.1 | dashboard-implementer | feita | Fixar versões com pip-tools a partir de um `requirements.in`. Declarar `branca`. Tirar `gunicorn` e `python3-gdal` do Dockerfile e testar a remoção de `gdal-bin` e `libgdal-dev`. | Build ok e `import geopandas` ok dentro da imagem. |
| T7.2 | dashboard-implementer | feita | Dockerfile com base `python:3.13.11-slim-trixie`, sem pacotes GDAL do sistema, usuário sem privilégio e `HEALTHCHECK`. O `publish-docker.sh` constrói no formato docker para o podman manter o healthcheck. Imagem testada localmente: 795 MB contra 1.020 MB da 1.1.1. | Container saudável localmente. |
| T7.3 | dashboard-implementer | parcial | Feito: sem `maxCacheSize`, upload de 1 MB e `runOnSave`/`fileWatcherType` de produção por variável de ambiente na imagem. Falta testar `enableXsrfProtection = true` atrás do proxy de produção. | App sobe sem avisos de configuração. |
| T7.4 | dashboard-implementer | feita | Trocar `use_container_width` por `width="stretch"` e `utcnow()` por `datetime.now(timezone.utc)`. | Nenhum `DeprecationWarning` do projeto no pytest. |
| T7.5 | dashboard-implementer | feita | Alinhar `.python-version`, `.tool-versions` e Dockerfile na mesma versão de Python. | Os três arquivos iguais. |
| T7.6 | integration-tester | parcial | Workflow `.github/workflows/testes.yml` no próprio repositório do dashboard, que é onde os PRs acontecem, rodando `ruff` e `pytest`. Falta ver o primeiro run verde depois do push. | Workflow verde num PR de teste. |
| T7.7 | Humano + dashboard-implementer | pendente | S8: você confirma os direitos de uso, e as imagens externas passam para `assets/`, servidas localmente. | Nenhum `img` ou `url()` apontando para imgur ou idace. |
| T7.8 | dashboard-implementer | feita | S3, decisão D-5: o miniserver 1.2.0 entrega o nome protegido em `/dados_fundiarios` e `/geojson`, e o pseudônimo `id_proprietario`, um HMAC do nome normalizado. O Gini do dashboard agrupa pelo pseudônimo e dá os mesmos resultados: 134.315 proprietários nos dois modos. Feito em 30/09. | Decisão registrada. |

### Trilha G: GeoAPI do IDACE e atualização mensal

Trilha paralela no miniserver. A atualização mensal depende da importação da GeoAPI, que hoje tem um problema de comunicação. Deve respeitar a decisão de separar a importação num Carregador de Dados.

| ID | Executor | Status | Tarefa | Aceite |
|---|---|---|---|---|
| TG.1 | Claude | feita | Diagnóstico da comunicação com a GeoAPI do IDACE, sem editar nada. Resultado na seção Diagnóstico da GeoAPI. Feito em 29/09. | Relatório com a causa provável e um passo a passo para reproduzir. |
| TG.5 | Humano | pendente | Acionar o IDACE: o proxy da GeoAPI responde 502 Bad Gateway, então o serviço por trás dele está fora do ar. | GeoAPI responde 401 sem token e 200 com token. |
| TG.2 | miniserver-implementer | feita | Importador da GeoAPI corrigido: quatro nomes de município errados (Granjeiro, Limoeiro do Norte, Tabuleiro do Norte e Piquet Carneiro), HTTPS, paginação, erro claro sem `TOKEN_GEOAPI`, nova tentativa só em falha de rede ou 5xx, e execução sem terminal. A cópia comentada de 464 linhas foi removida. Feito em 30/09. | Importação completa sem erro e sem duplicar registros. |
| TG.3 | integration-tester | parcial | Mecanismo testado localmente: uma carga nova muda a versão e o dashboard recarrega. Falta observar a primeira carga mensal em produção. | Teste ponta a ponta. |
| TG.6 | Claude | feita | Duplicação B10: cada tabela é trocada inteira numa única transação, e o registro de cargas guarda a data de cada uma. Validado no banco local: um banco já duplicado voltou às contagens corretas. Feito em 30/09. | Reiniciar o container não altera as contagens. |
| TG.7 | Claude | feita | Terra-AI: o token passou a enviar `aud` e `iss`, validado contra o miniserver novo. Feito em 30/09. | Terra-AI autentica no miniserver 1.2.0. |
| TG.8 | Humano | parcial | Imagens 1.2.0 publicadas em 30/09, com as tags `1.2.0` e `latest`, e conferidas no Docker Hub: sem segredos, sem root e com healthcheck. Falta implantar miniserver e dashboard juntos, com a stack atualizada. Passos em Próximos passos. | As duas versões no ar e as páginas com dados. |
| TG.4 | miniserver-implementer + dashboard-implementer | feita | Endpoint `/versao_dados`, alimentado pelo registro de cargas do importador. O dashboard confere a versão a cada 5 minutos e descarta o cache quando ela muda. Feito em 30/09. | Dados novos visíveis logo após a importação. |

## 3. Próximos passos

1. No Portainer, atualize a stack com o `docker-compose.stack.yml` do superprojeto. Ele passa ao `dfundce` a mesma `JWT_SECRET` do `tgdmserver`.
2. Implante `tgdmserver` e `dfundce` juntos. O miniserver 1.2.0 recusa tokens sem `aud`/`iss`, e o dashboard 1.2.0 agrupa o Gini pelo pseudônimo. Uma versão sem a outra quebra os mapas.
3. Na primeira subida, o miniserver refaz a carga e elimina as duplicatas. Leva alguns minutos, e o healthcheck espera até 15.
4. Confira as páginas. A contagem do mapa de Assentamentos deve cair para o número real, se havia duplicatas em produção.
5. Faça a primeira rotação dos segredos (T0.4) e apague as tags antigas.

## 4. Decisões em aberto

| ID | Decisão | Bloqueia |
|---|---|---|
| D-2 | Manter `plot_cadastro_pizza_estilo_original` e a aba "Geocadastro", hoje comentada? | T1.1 |
| D-7 | Trocar os gráficos matplotlib por gráficos nativos do Streamlit, que renderizam no navegador? | T5.5 |

## 5. Resultados de desempenho

Mesmo benchmark (`tests/benchPaginas.py`) e mesmos dados sintéticos antes e depois: 184 municípios, 30.000 imóveis, 600 assentamentos e 150 reservatórios, com a API simulada sem latência. Em produção, cada requisição ainda soma a latência da rede.

| Página | Requisições antes | Requisições depois | Interação antes (s) | Interação depois (s) | Mapa antes (KB) | Mapa depois (KB) |
|---|---|---|---|---|---|---|
| Início | 201 | 0 | 0.02 | 0.01 | sem mapa | sem mapa |
| Gráficos | 201 | 15 | 1.08 | 0.10 | sem mapa | sem mapa |
| Predominância | 202 | 16 | 0.29 | 0.10 | 392 | 394 |
| Malha Fundiária | 218 | 4 | 0.93 | 0.23 | 1616 | 1390 |
| Concentração (Gini) | 202 | 16 | 0.67 | 0.34 | 913 | 528 |
| Assentamentos | 206 | 3 | 2.67 | 0.25 | 3656 | 1511 |
| Hidrográfico | 205 | 4 | 0.42 | 0.42 | 1538 | 1492 |
| Escolas do Campo | 203 | 2 | 0.20 | 0.20 | 1223 | 1203 |
| Sobre | 201 | 0 | 0.04 | 0.03 | sem mapa | sem mapa |

## 6. Diagnóstico da GeoAPI (TG.1)

- Em 29/09/2026 às 17h27, o endpoint usado pelo importador respondeu **502 Bad Gateway** pelo proxy `openresty` do IDACE, com e sem token. O endereço em HTTP redireciona para HTTPS, e o HTTPS responde 502. O serviço por trás do proxy está fora do ar ou inacessível. Só o IDACE resolve isso (TG.5).
- A lista fixa de municípios do importador tinha quatro nomes errados: Granjeiro, Limoeiro do Norte, Tabuleiro do Norte e Piquet Carneiro. Esses municípios nunca eram importados. O relatório anterior citava só dois, porque a conferência leu por engano uma cópia comentada da lista. Corrigido na 1.2.0.
- O importador pedia uma única página de até 10.000 registros por município, e um município maior era cortado sem aviso. Na 1.2.0 ele pagina até a última página.
- A URL base usava HTTP e enviava o token antes do redirecionamento para HTTPS. Corrigido na 1.2.0.
- Sem `TOKEN_GEOAPI`, o importador usava um token vazio. Na 1.2.0 ele para com uma mensagem clara.
- Erros 4xx disparavam cinco novas tentativas inúteis. Na 1.2.0 só falhas de rede e erros 5xx são repetidos.
- O importador dependia de terminal por causa da barra de progresso em `curses`. Na 1.2.0 ele registra o progresso em log quando não há terminal.

## 7. Checklist

### Feito

- [x] Dashboard reestruturado: `app.py` caiu de 1.422 para 22 linhas, com uma página por módulo e navegação dirigida por tabela.
- [x] Camada única de API: `config.py`, `apiCliente.py` e `repositorio.py` substituem 4 cópias do token JWT e 3 da função de acesso à API.
- [x] Componentes compartilhados de mapa, interface, classificação e privacidade.
- [x] Bugs B1 a B9 corrigidos, cada um com teste de regressão.
- [x] LGPD: nome de pessoa física não chega mais ao navegador (D-5).
- [x] Escape de HTML em todo dado vindo da API, inclusive nos tooltips do folium.
- [x] Mensagens de erro sem URL interna e com registro em log.
- [x] Menu lateral sem JavaScript injetado nem iframes.
- [x] Desempenho: carga fria com no máximo 16 requisições por página, contra cerca de 200. Tabela abaixo.
- [x] Nomes em camelCase em todo o código, com teste que cobra a convenção.
- [x] Código comentado e sem uso removido. Doze arquivos sem uso em `arquivos-sem-uso/` para revisão.
- [x] Suíte de testes reescrita: 285 testes, sem avisos, contra 143 com 220 avisos. Lint com ruff sem apontamentos.
- [x] Dependências fixadas nas versões testadas, com `scripts/fixarDependencias.py`.
- [x] Imagem Docker sem GDAL do sistema, sem root, com healthcheck e sem `secrets.toml`, testada localmente.
- [x] `JWT_SECRET` ligado ao ambiente, na stack e no compose, com confirmação no script de publicação.
- [x] Procedimento anual de rotação em `doc/rotacao_segredos.md`.
- [x] Workflow de CI no repositório do dashboard.
- [x] README atualizado e definições dos agentes alinhadas à estrutura nova.
- [x] Diagnóstico da GeoAPI do IDACE (TG.1).
- [x] Versão 1.2.0 do miniserver: carga sem duplicação (B10), registro de cargas e `/versao_dados`, nomes protegidos e pseudônimo na API, JWT com `aud` e `iss`, CORS configurável, cache das listas com prazo e configuração de listas por variável de ambiente corrigida.
- [x] Importador da GeoAPI corrigido: quatro municípios, HTTPS, paginação, token, novas tentativas e execução sem terminal.
- [x] Imagem do miniserver sem root, com healthcheck, base Debian 13, dependências fixadas e sem ferramentas de compilação.
- [x] Dashboard 1.2.0: token com `aud` e `iss`, cache que acompanha a versão dos dados e Gini pelo pseudônimo, com os mesmos resultados.
- [x] Terra-AI: token com `aud` e `iss`.
- [x] Integração testada com os dados reais: miniserver e dashboard em container, só com variáveis de ambiente.
- [x] Imagens 1.2.0 do miniserver e do dashboard publicadas no Docker Hub e conferidas.

### Falta fazer

**Você**

- [ ] TG.8: implantar miniserver e dashboard 1.2.0 juntos, com a stack atualizada.
- [ ] T0.4: primeira rotação dos segredos e remoção das tags antigas do Docker Hub.
- [ ] TG.5: acionar o IDACE sobre o 502 da GeoAPI.
- [ ] T1.4: revisar a pasta `arquivos-sem-uso/`.
- [ ] T7.7: confirmar os direitos de uso das imagens hoje carregadas do imgur e do site do IDACE.
- [ ] Decidir D-2 (gráfico de Geocadastro) e D-7 (gráficos nativos).
- [ ] Enviar os commits ao GitHub. Nada foi enviado.

**Validação em produção**

- [ ] T0.5: conferir o JWT depois da rotação.
- [ ] TG.3: acompanhar a primeira carga mensal com o endpoint de versão.
- [ ] T7.6: ver o primeiro run verde do CI depois do push.
- [ ] T7.3: testar a proteção XSRF atrás do proxy.

**Fora do escopo desta rodada**

- [ ] Fixar a versão do `postgis` na stack. Antes, confira a versão em uso em produção com `SELECT version()`, porque trocar de versão principal exige migrar o volume de dados.
- [ ] Avaliar se a porta 8000 do miniserver precisa continuar publicada no host.
- [ ] A imagem do miniserver leva os CSVs com nomes de proprietários, porque a carga roda na inicialização. Mantenha o repositório privado até a separação do Carregador de Dados.
- [ ] Atualizar os diagramas em `doc/*.puml`.


## 8. Como acionar

Peça por ID de tarefa, por exemplo "execute a T0.1 do plano em `dashboard_fundiario_ceara/doc/plano_melhoria_codigo.md`". O agente lê a linha da tarefa, o achado correspondente e as regras da seção 2.1 antes de começar.
