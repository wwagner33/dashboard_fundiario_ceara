# modules/paginaInicio.py
"""Página inicial: apresentação da plataforma, equipes e links institucionais."""

import streamlit as st


def renderizar() -> None:
    with st.container():
        
        st.markdown(
            """
            <div class="minha-div">
                <img src="https://i.imgur.com/6Hk77Gg.png" alt="Imagem do IDACE">
            </div>
            <div class="minha-div">
                <img src="https://i.imgur.com/N1Ymd3d.png" alt="Imagem do IDACE">
            </div>
            """,
            unsafe_allow_html=True
        )
        st.html("""
        
        <div class="container-estilizado">
            <!-- Primeira Seção -->
            <div>
                <h3>Equipe Idace</h3>
                <span ></span>
                <span ></span>

                <span class="titulo">Superintendente</span>
                <span class="subtitulo">João Alfredo Telles Melo</span>
                
                <span class="titulo">Superintendente Adjunto</span>
                <span class="subtitulo">Antônio Rodrigues de Amorim</span>
            </div>
            
            <!-- Segunda Seção -->
            <div>
                <span class="titulo">Diretora Administrativo-Financeira</span>
                <span class="subtitulo">Claudecilia de Oliveira Teixeira</span>
                
                <span class="titulo">Diretor Técnico de Operações</span>
                <span class="subtitulo">Paulo H. Magalhães Lobo</span>
                
                <span class="titulo">Assessor Jurídico</span>
                <span class="subtitulo">Ricardo Sá Benevides Magalhães</span>
                
                <span class="titulo">Assessor de Comunicação</span>
                <span class="subtitulo">Marina Holanda Pinheiro</span>
                
                <span class="titulo">Assessoria de Desenvolvimento Institucional (Adins)</span>
                <span class="subtitulo">Maria das Graças Farias Pedrosa</span>
                
                <span class="titulo">Ouvidoria </span>
                <span class="subtitulo">Domingos Rocha</span>
            </div>
            
            <!-- Terceira Seção (Imagem como link) -->
            
                <a href="https://drive.google.com/file/d/1pdqD_55RAo3UNkp7ggx1MUGcKaH0UtSZ/view?usp=drive_link" target="_blank">
                    <img src="https://www.idace.ce.gov.br/wp-content/uploads/sites/84/2021/07/idace_apresentacao_banner.png" alt="Imagem" class="imagem-link">
                </a>
            
        </div>
        """)
        st.html("""
                <div class="container-estilizado2">
                <h4>Bem-vindo(a) à Terra.Ce</h4>
                <p> 
                    “A plataforma Terra.CE é fruto de uma parceria de inovação pública entre IDACE a  Universidade Federal do Ceará e a FUNCAP. A sistematização dos dados aqui apresentados é fruto do Projeto Cientista Chefe Governança Fundiária e Ambiental - CCTERRA, que visa fortalecer a gestão da terra no Ceará por meio da pesquisa e da ciência de dados. Esta plataforma disponibiliza indicadores e mapas interativos para subsidiar políticas públicas baseadas em evidências, promovendo uma governança integrada, sustentável e transparente. Compreender as dinâmicas territoriais é essencial para um Ceará mais justo social e ambientalmente.”
                </p>
                </div>
                """)
        st.html("""
        
        <div class="container-estilizado ">
            <!-- Primeira Seção -->
            <div>
                <h3>Equipe TerraCE</h3>
                <span class="titulo">Coordenadora do Projeto/UFC</span>
                <span class="subtitulo">Maria Inês Escobar da Costa Casimiro</span>

                <span class="titulo">Coordenador Técnico de Sistemas/UFC</span>
                <span class="subtitulo">Wellington Wagner Ferreira Sarmento</span>

                <span class="titulo">Coordenadora de Análises Quantitativas/UFC</span>
                <span class="subtitulo">Maria de Nazaré Moraes Soares</span>

                <span class="titulo">Coordenadora de Análises Qualitativas/UFC</span>
                <span class="subtitulo">Kelly Maria Gomes Menezes</span>

                <span class="titulo">Coordenadora de Ações de Campo</span>
                <span class="subtitulo">Christine Farias Coelho</span>

                <span class="titulo">Pesquisadora</span>
                <span class="subtitulo">Erika Roanna da Silva</span>
            </div>
            
            <!-- Segunda Seção -->
            <div>
                <span class="titulo">Pesquisadora</span>
                <span class="subtitulo">Bárbara Sheyla Pereira Lima Moreira</span>

                <span class="titulo">Pesquisador</span>
                <span class="subtitulo">Bruno Silva Pereira</span>

                <span class="titulo">Pesquisador</span>
                <span class="subtitulo">André Lucas de Oliveira Domingues</span>

                <span class="titulo">Pesquisador</span>
                <span class="subtitulo">Wesley Barbosa Martins Ribeiro</span>

                <span class="titulo">Pesquisadora</span>
                <span class="subtitulo">Juliana Azevedo da Silva</span>

                <span class="titulo">Pesquisador</span>
                <span class="subtitulo">Fernando Abreu</span>
            </div>
            
        </div>
        """)
        st.html("""<section class="AcessoRapido">
      <div class="wrapper">
        <div class="row">
          <h4>Acesso Rápido</h4>

          <nav class="MenuAcessos">
            <div class="acesso-rapido">
              <ul id="menu-acesso-rapido-footer" class="menu">
                <li
                  id="menu-item-870"
                  class="portal menu-item menu-item-type-custom menu-item-object-custom menu-item-870"
                >
                  <a href="https://cearatransparente.ce.gov.br" target="_blank"
                    ><i class="PortalTransparencia"></i>
                    <span>
                      Ceará<br />
                      Transparente
                    </span>
                  </a>
                </li>
                <li
                  id="menu-item-871"
                  class="acesso menu-item menu-item-type-custom menu-item-object-custom menu-item-871"
                >
                  <a href="http://cartadeservicos.ce.gov.br/" target="_blank"
                    ><i class="AcessoCidadao"></i>
                    <span> Carta de Serviços<br />do Cidadão </span>
                  </a>
                </li>
                <li
                  id="menu-item-872"
                  class="lei menu-item menu-item-type-custom menu-item-object-custom menu-item-872"
                >
                  <a
                    href="https://cearatransparente.ce.gov.br/portal-da-transparencia/acesso-a-informacao?locale=pt-BR"
                    target="_blank"
                    ><i class="AcessoInformacao"></i>
                    <span>
                      Lei geral de<br />
                      acesso à informação
                    </span>
                  </a>
                </li>
                <li
                  id="menu-item-873"
                  class="diario menu-item menu-item-type-custom menu-item-object-custom menu-item-873"
                >
                  <a
                    href="http://pesquisa.doe.seplag.ce.gov.br/"
                    target="_blank"
                    ><i class="DiarioOficial"></i>

                    <span>
                      Diário<br />
                      Oficial
                    </span>
                  </a>
                </li>
                <li
                  id="menu-item-874"
                  class="legislacao menu-item menu-item-type-custom menu-item-object-custom menu-item-874"
                >
                  <a href="https://www.al.ce.gov.br/" target="_blank"
                    ><i class="Legislacao"></i>

                    <span>
                      Legislação<br />
                      Estadual
                    </span>
                  </a>
                </li>
                <li
                  id="menu-item-61919"
                  class="acoes menu-item menu-item-type-post_type menu-item-object-page menu-item-61919"
                >
                  <a
                    href="https://www.ceara.gov.br/wp-content/uploads/2025/07/Codigo-de-Etica.pdf"
                    target="_blank"
                    ><i class="AcoesGoverno"></i>
                    <span> Código de Ética dos Servidores Públicos </span>
                  </a>
                </li>
              </ul>
            </div>
          </nav>
        </div>
      </div>
    </section>
    <footer>
      <div class="wrapper">
        <div class="row Infos" style="border-top: none">
          <div class="dt-2 NomeSite">
            <a class="link-gov" href="http://WWW.IDACE.CE.GOV.BR">
              <h2>IDACE.CE.GOV.BR</h2>
            </a>
          </div>

          <div class="dt-10 Direitos">
            <div>
              <div class="textwidget">
                <div class="box">
                  <h2>IDACE</h2>
                  <p>
                    Av. Bezerra de Menezes, 1820 - São Gerardo<br />
                    Fortaleza, CE<br />
                    CEP: 60.325-001
                  </p>
                </div>
                <div class="box">
                  <h2>Horário de Atendimento</h2>
                  <p>8h às 12h</p>
                  <p>13h às 17h</p>
                </div>

                <div class="box">
                  <h2 class="canais">Nossos canais</h2>
                  <div class="redes">
                    <ul class="menu">
                      <li class="facebook redesLinkRodape">
                        <a
                          href="https://www.facebook.com/idace.gov"
                          style="overflow: hidden"
                          target="_blank"
                          >Facebook</a
                        >
                      </li>
                      <li class="instagram redesLinkRodape">
                        <a
                          href="https://www.instagram.com/idace.ce/"
                          style="overflow: hidden"
                          target="_blank"
                          >Instagram</a
                        >
                      </li>
                    </ul>
                  </div>
                </div>

                <div class="box copyright">
                  <p>
                    © 2017 - 2025 – governo do estado do ceará<br />
                    todos os direitos reservados
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </footer>""")
