import sys
import pandas as pd
import streamlit as st
from streamlit_community_navigation_bar import st_navbar
from client_control import ClientControl
import altair as alt

GIST_ID_FIXO = "68bb78ccf423bb9f3b3af43bc569e3ba"
st.set_page_config(page_title="ClientControl", layout="centered")
st.title("Bem-vindo ao Assistente de Cobrança Lulu 💸")

# Estilo da navbar
custom_styles = {
    "nav": {
        "background-color": "#121212",
        "padding": "10px 30px",
        "border-radius": "10px",
        "box-shadow": "0 2px 6px rgba(0, 0, 0, 0.2)",
    },
    "span": {
        "color": "#e0e0e0",
        "font-size": "16px",
        "padding": "10px 20px",
        "border-radius": "6px",
        "margin": "0 10px",
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
    st.info("Para começar, insira seu Personal Access Token (PAT) do GitHub.")
    with st.form("login_form"):
        st.text_input("ID do Gist (Fixo)", value=GIST_ID_FIXO, disabled=True)
        token_input = st.text_input("Token de Acesso do GitHub", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if not token_input:
                st.warning("Por favor, preencha o Token de Acesso.")
            else:
                try:
                    controle = ClientControl(token=token_input, gist_id=GIST_ID_FIXO)
                    st.session_state.controle = controle
                    st.session_token = token_input
                    st.rerun()
                except Exception as e:
                    st.error(f"Falha no login: {e}")
else:
    controle: ClientControl = st.session_state.controle
    pagina = st_navbar(["Home", "Consultar", "Cadastrar","Dashboard", "Sobre"], styles=custom_styles)

    st.markdown("---")

    # Página: HOME
    if pagina == "Home":
        st.write("Selecione uma das opções acima para iniciar o controle de cobranças.")

    # Página: CONSULTAR
    elif pagina == "Consultar":
        st.subheader("🔍 Consultar Clientes e Parcelas")
        dados = controle.consultar_dados()

        if not dados:
            st.info("Nenhum dado disponível.")
        else:
            # Explodir as parcelas
            df = pd.json_normalize(
                dados,
                record_path='parcelas',
                meta=['nome'],
                errors='ignore'
            )
            df['valor'] = df['valor'].astype(float)

            st.markdown("### 📝 Editar Parcelas")
            df_editado = st.data_editor(
                df,
                num_rows="fixed",
                use_container_width=True,
                disabled=["nome", "vencimento", "vencimento"], 
                column_config={
                    "valor": st.column_config.NumberColumn("Valor (R$)", min_value=0.01, step=1.0),
                    "paga": st.column_config.CheckboxColumn("Paga"),
                }
            )

            if st.button("💾 Salvar Alterações"):
                dados_atualizados = controle.consultar_dados()
                for _, row in df_editado.iterrows():
                    for dev in dados_atualizados:
                        if dev["nome"] == row["nome"]:
                            for parcela in dev["parcelas"]:
                                if parcela["vencimento"] == row["vencimento"]:
                                    parcela["valor"] = float(row["valor"])
                                    parcela["paga"] = bool(row["paga"])
                if controle.atualizar_gist(dados_atualizados):
                    st.success("✅ Alterações salvas com sucesso!")
                    st.rerun()

    # Página: CADASTRAR
    elif pagina == "Cadastrar":
        st.subheader("📝 Cadastrar Novo Devedor")
        with st.form("cadastro_form"):
            nome = st.text_input("Nome do Devedor")
            n_parcelas = st.number_input("Número de Parcelas", min_value=1, value=1)
            valor_parcela = st.number_input("Valor por Parcela", min_value=0.01, format="%.2f")
            vencimento_inicial = st.date_input("Data de Vencimento Inicial")
            enviar = st.form_submit_button("Cadastrar")

            if enviar:
                controle.cadastrar_novo_devedor(
                    nome=nome,
                    n_parcelas=n_parcelas,
                    vl_par=valor_parcela,
                    p_vencimento=vencimento_inicial.strftime("%Y-%m-%d")
                )
                st.success(f"✅ Devedor '{nome}' cadastrado com sucesso!")

    # Página: DASHBOARD (com Tabela Dinâmica e Filtros)
    elif pagina == "Dashboard":
        st.subheader("📊 Dashboard de Cobranças")

        dados = controle.consultar_dados()
        if not dados:
            st.info("Nenhum dado para exibir no dashboard.")
            st.stop() # Para a execução se não houver dados

        # ---------------- ETAPA 1: PREPARAÇÃO DOS DADOS ----------------
        # Normaliza e prepara o DataFrame principal uma única vez
        df = pd.json_normalize(
            dados,
            record_path="parcelas",
            meta=["nome"],
            errors="ignore"
        )
        df["valor"] = pd.to_numeric(df["valor"], errors='coerce').fillna(0)
        df["paga"] = df["paga"].astype(bool)
        df["vencimento"] = pd.to_datetime(df["vencimento"])
        
        # Cria colunas auxiliares que serão usadas nos filtros e na tabela
        df['ano'] = df['vencimento'].dt.year
        df['mes_num'] = df['vencimento'].dt.month
        df['status'] = df['paga'].map({True: 'Valor Pago', False: 'Valor a Receber'})

        # ---------------- ETAPA 2: FILTROS INTERATIVOS ----------------
        st.markdown("### Filtros")
        
        # Opções para os filtros
        anos_disponiveis = sorted(df['ano'].unique(), reverse=True)
        opcoes_ano = ["Todos"] + anos_disponiveis
        
        meses_nomes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", 
                       "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        opcoes_mes = ["Todos"] + meses_nomes

        col1, col2 = st.columns(2)
        with col1:
            ano_selecionado = st.selectbox("Selecione o Ano", options=opcoes_ano)
        with col2:
            mes_selecionado = st.selectbox("Selecione o Mês", options=opcoes_mes)

        # Aplica os filtros ao DataFrame
        df_filtrado = df.copy()
        if ano_selecionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado['ano'] == ano_selecionado]
        
        if mes_selecionado != "Todos":
            # Converte o nome do mês para número para poder filtrar
            mes_numero = opcoes_mes.index(mes_selecionado)
            df_filtrado = df_filtrado[df_filtrado['mes_num'] == mes_numero]

        st.markdown("---")

        # ---------------- ETAPA 3: EXIBIÇÃO DOS DADOS FILTRADOS ----------------
        
        if df_filtrado.empty:
            st.warning("Nenhum dado encontrado para a seleção de filtro atual.")
        else:
            st.markdown("### Resumo Financeiro")
            # Métricas calculadas com base nos dados JÁ FILTRADOS
            total_pago = df_filtrado[df_filtrado["paga"]]["valor"].sum()
            total_aberto = df_filtrado[~df_filtrado["paga"]]["valor"].sum()
            valor_total = total_pago + total_aberto
            
            m1, m2, m3 = st.columns(3)
            m1.metric("💰 Total Recebido", f"R$ {total_pago:,.2f}")
            m2.metric("📬 Total a Receber", f"R$ {total_aberto:,.2f}")
            m3.metric("📋 Total Geral", f"R$ {valor_total:,.2f}")

            st.markdown("---")
            st.markdown("### Detalhamento Mensal")

            # Cria uma coluna de mês com nome para a tabela
            df_filtrado['mes_nome'] = df_filtrado['mes_num'].apply(lambda x: meses_nomes[x-1])
            
            # Cria a tabela dinâmica (pivot table)
            tabela_resumo = pd.pivot_table(
                df_filtrado,
                values='valor',
                index='status',          # Linhas da tabela
                columns='mes_nome',      # Colunas da tabela
                aggfunc='sum',           # O que fazer com os valores: somar
                fill_value=0,            # Preencher células vazias com 0
            )

            # Ordena as colunas da tabela na ordem correta dos meses
            ordem_meses = [mes for mes in meses_nomes if mes in tabela_resumo.columns]
            tabela_resumo = tabela_resumo[ordem_meses]

            # Formata os valores como moeda para exibição
            styled_table = tabela_resumo.style.format("R$ {:,.2f}")

            st.dataframe(styled_table, use_container_width=True)


    elif pagina == "Sobre":
        st.subheader("ℹ️ Sobre o Projeto")
        st.markdown("""
        Este assistente foi criado para facilitar o controle de cobranças de forma simples e intuitiva.
        
        **Funcionalidades:**
        - Cadastro de devedores
        - Parcelamento automático
        - Armazenamento seguro via GitHub Gist
        
        Desenvolvido com ❤️ por [Diego](https://github.com/diego).
        """)
