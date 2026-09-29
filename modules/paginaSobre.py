# modules/paginaSobre.py
"""Página Sobre: o projeto Terra.Ce, equipe, licença e apoio."""

import streamlit as st


def renderizar() -> None:
    st.markdown(
        """
        <div class="minha-div">
            <img src="https://i.imgur.com/N1Ymd3d.png" alt="Imagem do IDACE">
        </div>
        """,
        unsafe_allow_html=True
    )
    with st.container():
        st.html("""<div class="teste"></div>""")
        st.html("""
                <div class="container-estilizado2">
                <h4>O projeto Terra.Ce</h4>
                <p> 
                  Aplicação de painéis contendo dados estatísticos e geoespaciais 
                  da malha fundiária cearense desenvolvido, principalmente, a partir 
                  dos dados cadastrados no Instituto de Desenvolvimento Agrário do Ceará (IDACE).
                  Este software faz parte das ações realizadas no âmbito do projeto 
                  <strong>Cientista Chefe Terra  de Governança Fundiária e Ambiental</strong>, parceria entre o IDACE, a Universidade Federal do Ceará (UFC) e a Fundação Cearense de Apoio ao Desenvolvimento Científico e Tecnológico (Funcap).
                </p>
                <p style='padding-top: 5px;'> <i>Coordenadora Geral </br> Maria Inês Escobar da Costa Casimiro </i></p>
                </div>
                """)

        # Equipe de desenvolvimento
        st.html("""
        <div class="container-estilizado ">
            <!-- Primeira Seção -->
            <div>
                <h3>Equipe de Desenvolvimento - TerraCE</h3>
                <span class="titulo">Coordenadora Técnico de Sistemas/UFC</span>
                <span class="subtitulo">Wellington Wagner Ferreira Sarmento</span>

                <span class="titulo">Doutoranda MDCC/UFC</span>
                <span class="subtitulo">Me. Patrícia de Sousa Paula</span>

            </div>
            
            <!-- Segunda Seção -->
            <div>
                <span class="titulo">Pesquisador/UFC</span>
                <span class="subtitulo">André Lucas de Oliveira Domingues </span>

                <span class="titulo">Pesquisador/UFC</span>
                <span class="subtitulo">Wesley Barbosa Martins Ribeiro</span>
            </div>
            
        </div>
        """)

        # Licença de Uso
        st.html("""
        <div class="container-estilizado ">
            <!-- Primeira Seção -->
            <div>
                <h3>Licença de Uso</h3>
              
                <span class="subtitulo"><a href="https://github.com/Projeto-Cientista-Chefe-Terra/dashboard_fundiario_ceara/blob/main/LICENSE" target="_blank" style='text-decoration: underline;'> GNU General Public License (GPL) </a></span>

                

            </div>
            
        </div>
        """)

        # Link para o projeto
        st.html("""
        <div class="container-estilizado ">
            <!-- Primeira Seção -->
            <div>
                <h3>Cientista Chefe Terra de Governança Fundiária e Ambiental</h3>
                <span class="titulo">Site Institucional</span>
                <span class="subtitulo">
                  <a href="https://ccterra-site.vercel.app" target="_blank" style='text-decoration: underline;'>https://ccterra-site.vercel.app</a>
                </span>

                <span class="titulo">Código Fonte</span>
                <span class="subtitulo">
                  <a href="https://github.com/Projeto-Cientista-Chefe-Terra" target="_blank" style='text-decoration: underline;'>https://github.com/Projeto-Cientista-Chefe-Terra</a>
                </span>

            </div>            
        </div>
        """)

        # Apoio
        st.html("""
        <div class="container-estilizado ">
            <!-- Primeira Seção -->
            <div>
                <h3>Apoio</h3>
            </div>            
        </div>
        """)
        
        st.html("""<div class="imgs_logo_apoio"></div>""")
        st.image("./assets/Logos.png", width="stretch")
