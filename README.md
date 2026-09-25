# dashboard_fundiario_ceara
Aplicação Web de Análise e Visualização dos dados de concentração fundiária do Ceará

## Requisitos Funcionais
| ID   | User Story                                                                                                                 |
| ---- | -------------------------------------------------------------------------------------------------------------------------- |
| RF01 | Como usuário, quero visualizar o mapa interativo das propriedades rurais do Ceará para analisar a concentração fundiária.  |
| RF02 | Como usuário, quero visualizar gráficos interativos (barra, pizza, cumulativo) das classificações das propriedades rurais. |
| RF03 | Como usuário, quero poder selecionar municípios específicos para filtrar a visualização dos mapas e gráficos.              |
| RF04 | Como usuário, quero acessar informações detalhadas sobre cada propriedade ao clicar no mapa.                               |

## Requisitos Não Funcionais
| ID    | Requisito Não Funcional                                                           |
| ----- | --------------------------------------------------------------------------------- |
| RNF01 | O sistema deve ser responsivo, funcionando bem em desktops e dispositivos móveis. |
| RNF02 | A aplicação deve carregar rapidamente gráficos e mapas (alta performance).        |
| RNF03 | O código deve ser modular, claro e bem documentado.                               |

## Camada base dos mapas (CARTO)

Os mapas usam os basemaps raster da CARTO, que desde 2025 exigem uma API key.
Sem a chave os tiles continuam sendo servidos, porém cobertos pela marca d'água
*API key required*.

A chave é lida por `modules/basemap.py`, nesta ordem de precedência:

1. variável de ambiente `CARTO_API_KEY`;
2. `st.secrets["CARTO_API_KEY"]`, vinda de `.streamlit/secrets.toml`.

Se nenhuma das duas estiver preenchida, o dashboard usa o OpenStreetMap como
camada base. Isso é proposital: um mapa com outra aparência é preferível a um
mapa com marca d'água.

### Restrição por domínio

A chave do projeto está restrita ao domínio `terrace.virtual.ufc.br` no painel
da CARTO. A validação é feita pelo cabeçalho `Referer` enviado pelo navegador,
então requisições de qualquer outra origem recebem HTTP 403 e os tiles ficam
cinza. Consequências práticas:

- em produção, basta a variável `CARTO_API_KEY` estar definida no container;
- em desenvolvimento local, `CARTO_API_KEY` deve ficar **vazia**, para que o
  OpenStreetMap seja usado. Para usar os tiles da CARTO localmente, libere
  `localhost` nas restrições da chave em <https://carto.com/basemaps/apikey>.

Como a checagem depende do navegador, o servidor não consegue validar a chave
sozinho: um teste feito a partir do backend é rejeitado mesmo com a chave certa.

### Configuração

| Ambiente          | Onde definir                                          |
| ----------------- | ----------------------------------------------------- |
| Desenvolvimento   | `.streamlit/secrets.toml` (mantido fora do git)       |
| docker-compose    | `.env`, repassado ao serviço `dfundce`                |
| Portainer         | variável de ambiente `CARTO_API_KEY` do container     |

No Portainer, cole o valor da chave **sem aspas**.

A atribuição da CARTO e do OpenStreetMap é obrigatória e já acompanha a camada
base em todos os mapas (<https://carto.com/attributions>).



