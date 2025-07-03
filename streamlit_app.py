import sys
import pandas as pd
import streamlit as st
from streamlit_community_navigation_bar import st_navbar
from client_control import ClientControl, toggle_menu
from streamlit_option_menu import option_menu
import altair as alt

GIST_ID_FIXO = "68bb78ccf423bb9f3b3af43bc569e3ba"
st.set_page_config(page_title="ClientControl", layout="wide")
st.title("📱 Bem-vindo ao Assistente de Cobrança Lulu 💸")

# Estilo da navbar (com padding menor)
custom_styles = {
    "nav": {
        "background-color": "#121212",
        "padding": "5px 10px",
        "border-radius": "10px",
        "box-shadow": "0 2px 6px rgba(0, 0, 0, 0.2)",
    },
    "span": {
        "color": "#e0e0e0",
        "font-size": "16px",
        "padding": "6px 12px",
        "border-radius": "6px",
        "margin": "0 6px",
        "transition": "all 0.2s ease-in-out",
        "font-weight": "500",
        "letter-spacing": "0.4px",
        "font-family": "'Inter', 'Segoe UI', sans-serif"
    },
    "hover": {
        "color": "#ffffff",
        "background-color": "#2a2a2a",
        "box-shadow": "inset 0 0 0 1px #444",
    },
    "active": {
        "color": "#ffffff",
        "background-color": "#0d6efd",
        "font-weight": "600",
        "box-shadow": "0 2px 8px rgba(13, 110, 253, 0.3)",
    }
}

# Autenticação
if 'controle' not in st.session_state:
    st.session_state.controle = None

if st.session_state.controle is None:
    st.info("Insira seu Token do GitHub para iniciar.")
    with st.form("login_form"):
        st.text_input("ID do Gist (Fixo)", value=GIST_ID_FIXO, disabled=True)
        token_input = st.text_input("Token de Acesso do GitHub", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if not token_input:
                st.warning("Por favor, preencha o Token.")
            else:
                try:
                    controle = ClientControl(token=token_input, gist_id=GIST_ID_FIXO)
                    st.session_state.controle = controle
                    st.rerun()
                except Exception as e:
                    st.error(f"Falha no login: {e}")
else:
    # A partir daqui, o usuário está logado.
    controle: ClientControl = st.session_state.controle
    
    # --- LÓGICA DO LAYOUT COM MENU RETRÁTIL ---

    # Inicializa os estados da sessão para o menu
    if "menu_visivel" not in st.session_state:
        st.session_state.menu_visivel = False  # Menu começa visível
    if "ultima_pagina" not in st.session_state:
        st.session_state.ultima_pagina = "Home"

    # Botão Hambúrguer no topo
    col1_button, _ = st.columns([0.05, 0.95])
    with col1_button:
        st.button("☰", on_click=toggle_menu, help="Abrir/Fechar Menu")

    # Lógica de exibição do Menu e Conteúdo
    if st.session_state.menu_visivel:
        # Divide a tela: menu à esquerda, conteúdo à direita
        col_menu, col_conteudo = st.columns([0.2, 0.8])
        
        with col_menu:
            # Usando option_menu para um menu vertical bonito
            pagina_selecionada = option_menu(
                menu_title=None,
                options=["Home", "Consultar", "Cadastrar", "Dashboard", "Sobre"],
                icons=["house-door-fill", "search", "pencil-square", "bar-chart-line-fill", "info-circle-fill"],
                default_index=["Home", "Consultar", "Cadastrar", "Dashboard", "Sobre"].index(st.session_state.ultima_pagina),
                styles={
                    "container": {"padding": "0!important", "background-color": "#0E1117"},
                    "icon": {"color": "#0d6efd", "font-size": "20px"}, 
                    "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#444"},
                    "nav-link-selected": {"background-color": "#0d6efd"},
                }
            )
    else:
        # Se o menu estiver oculto, o conteúdo ocupa toda a tela
        col_conteudo = st.container()
        pagina_selecionada = st.session_state.ultima_pagina

    # Guarda a última seleção para quando o menu for fechado/reaberto
    st.session_state.ultima_pagina = pagina_selecionada

    # --- RENDERIZAÇÃO DO CONTEÚDO DA PÁGINA ---
    with col_conteudo:
        if pagina_selecionada == "Home":
            st.subheader("🏠 Home")
            st.markdown("---")
            st.info("👈 Use o menu para navegar pelas funcionalidades. Clique no '☰' para ocultá-lo.")

        elif pagina_selecionada == "Consultar":
            st.subheader("🔍 Consultar e Editar Parcelas")
            st.markdown("---")
            dados = controle.consultar_dados()

            if not dados:
                st.info("Nenhum dado disponível.")
            else:
                df = pd.json_normalize(dados, record_path='parcelas', meta=['nome'], errors='ignore')
                df['valor'] = df['valor'].astype(float)

                df_editado = st.data_editor(
                    df,
                    use_container_width=True,
                    disabled=["nome", "vencimento"],
                    column_config={
                        "nome": st.column_config.TextColumn("Nome"),
                        "valor": st.column_config.NumberColumn("Valor (R$)", min_value=0.01, step=1.0, format="R$ %.2f"),
                        "paga": st.column_config.CheckboxColumn("Paga"),
                        "vencimento": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY")
                    },
                    key="data_editor_consultar"
                )

                if st.button("💾 Salvar Alterações"):
                    dados_atualizados = controle.consultar_dados()
                    # Mapeia as alterações de forma mais eficiente
                    edit_map = {(row["nome"], row["vencimento"]): (row["valor"], row["paga"]) for _, row in df_editado.iterrows()}
                    
                    for dev in dados_atualizados:
                        for parcela in dev["parcelas"]:
                            key = (dev["nome"], parcela["vencimento"])
                            if key in edit_map:
                                parcela["valor"], parcela["paga"] = edit_map[key]
                                parcela["valor"] = float(parcela["valor"])
                                parcela["paga"] = bool(parcela["paga"])
                                
                    if controle.atualizar_gist(dados_atualizados):
                        st.success("✅ Alterações salvas com sucesso!")
                        st.rerun()

        elif pagina_selecionada == "Cadastrar":
            st.subheader("📝 Cadastrar Novo Devedor")
            st.markdown("---")
            with st.form("cadastro_form"):
                nome = st.text_input("Nome do Devedor")
                n_parcelas = st.number_input("Número de Parcelas", min_value=1, value=1)
                valor_parcela = st.number_input("Valor por Parcela (R$)", min_value=0.01, format="%.2f")
                vencimento_inicial = st.date_input("Data de Vencimento Inicial")
                enviar = st.form_submit_button("Cadastrar")

                if enviar:
                    if nome and valor_parcela:
                        controle.cadastrar_novo_devedor(
                            nome=nome,
                            n_parcelas=n_parcelas,
                            vl_par=valor_parcela,
                            p_vencimento=vencimento_inicial.strftime("%Y-%m-%d")
                        )
                        st.success(f"✅ Devedor '{nome}' cadastrado com sucesso!")
                        st.balloons()
                    else:
                        st.warning("Preencha o Nome e o Valor da Parcela.")

        elif pagina_selecionada == "Dashboard":
            st.subheader("📊 Dashboard de Cobranças")
            st.markdown("---")
            dados = controle.consultar_dados()
            if not dados:
                st.info("Nenhum dado para exibir.")
            else:
                df = pd.json_normalize(dados, record_path="parcelas", meta=["nome"], errors="ignore")
                if df.empty:
                    st.info("Nenhum dado de parcela para exibir.")
                else:
                    df["valor"] = pd.to_numeric(df["valor"], errors='coerce').fillna(0)
                    df["paga"] = df["paga"].astype(bool)
                    df["vencimento"] = pd.to_datetime(df["vencimento"])
                    df['ano'] = df['vencimento'].dt.year
                    df['mes_num'] = df['vencimento'].dt.month
                    df['status'] = df['paga'].map({True: 'Valor Pago', False: 'Valor a Receber'})

                    st.markdown("### Filtros")
                    anos_disponiveis = sorted(df['ano'].unique(), reverse=True)
                    meses_nomes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
                    opcoes_ano = ["Todos"] + anos_disponiveis
                    opcoes_mes = ["Todos"] + meses_nomes

                    ano_selecionado = st.selectbox("Ano", options=opcoes_ano)
                    mes_selecionado = st.selectbox("Mês", options=opcoes_mes)

                    df_filtrado = df.copy()
                    if ano_selecionado != "Todos":
                        df_filtrado = df_filtrado[df_filtrado['ano'] == ano_selecionado]
                    if mes_selecionado != "Todos":
                        mes_numero = opcoes_mes.index(mes_selecionado)
                        df_filtrado = df_filtrado[df_filtrado['mes_num'] == mes_numero]

                    st.markdown("---")

                    if df_filtrado.empty:
                        st.warning("Nenhum dado encontrado para os filtros aplicados.")
                    else:
                        total_pago = df_filtrado[df_filtrado["paga"]]["valor"].sum()
                        total_aberto = df_filtrado[~df_filtrado["paga"]]["valor"].sum()
                        valor_total = total_pago + total_aberto
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("💰 Total Recebido", f"R$ {total_pago:,.2f}")
                        col2.metric("📬 Total a Receber", f"R$ {total_aberto:,.2f}")
                        col3.metric("📋 Total Geral", f"R$ {valor_total:,.2f}")

                        st.markdown("### Detalhamento Mensal")
                        df_filtrado['mes_nome'] = df_filtrado['mes_num'].apply(lambda x: meses_nomes[x - 1])
                        tabela_resumo = pd.pivot_table(
                            df_filtrado,
                            values='valor',
                            index='status',
                            columns='mes_nome',
                            aggfunc='sum',
                            fill_value=0
                        )
                        ordem_meses = [mes for mes in meses_nomes if mes in tabela_resumo.columns]
                        if ordem_meses:
                            tabela_resumo = tabela_resumo[ordem_meses]
                            styled_table = tabela_resumo.style.format("R$ {:,.2f}")
                            st.dataframe(styled_table, use_container_width=True)
                        else:
                            st.info("Nenhum dado de valor para exibir na tabela de resumo mensal.")


        elif pagina_selecionada == "Sobre":
            st.subheader("ℹ️ Sobre o Projeto")
            st.markdown("---")
            st.markdown("""
            Este assistente foi criado para facilitar o controle de cobranças de forma simples e intuitiva.

            **Funcionalidades:**
            - Cadastro de devedores
            - Parcelamento automático
            - Armazenamento seguro via GitHub Gist
            - Dashboard para visualização financeira
            - Menu lateral retrátil para melhor experiência de uso

            Desenvolvido com ❤️ por [Diego](https://github.com/diego).
            """)
