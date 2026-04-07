import streamlit as st
import pandas as pd
import math
from datetime import datetime
from fpdf import FPDF
from supabase import create_client, Client

# --- 1. CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira linha) ---
st.set_page_config(page_title="VoltSpec Pro", layout="wide", page_icon="⚡")

# --- 2. CONEXÃO COM BANCO (SUPABASE) ---
URL_SUPA = "https://drhcokdzqycmdkshceub.supabase.co"
# Chave corrigida e completa
KEY_SUPA = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRyaGNva2R6cXljbWRrc2hjZXViIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUyNjA0MDQsImV4cCI6MjA5MDgzNjQwNH0.FrN2x_Tgq8m_ZIYCt6Ht0R3dMU3_RQUwGLAw3Pfgbm0"
def init_connection():
    try:
        return create_client(URL_SUPA, KEY_SUPA)
    except Exception as e:
        st.error(f"❌ Erro na conexão com o Supabase: {e}")
        return None

supabase = init_connection()

# --- 3. FUNÇÕES DE SINCRONIZAÇÃO ---
def carregar_perfil_supabase():
    if st.session_state.user:
        try:
            res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()
            if res.data:
                dados = res.data[0]
                st.session_state.nome_empresa = dados.get('nome_empresa', '')
                st.session_state.crt = dados.get('crt', '')
                st.session_state.telefone = dados.get('telefone', '')
                st.session_state.cnpj = dados.get('cnpj', '')
                st.session_state.endereco = dados.get('endereco', '')
                st.session_state.email_contato = dados.get('email_contato', '')
                return True
        except Exception as e:
            st.error(f"Erro ao puxar dados: {e}")
    return False

def salvar_perfil_supabase():
    if not st.session_state.user:
        st.error("❌ Você precisa estar logado!")
        return

def salvar_perfil_supabase():
    if 'user' not in st.session_state or st.session_state.user is None:
        st.error("❌ Você precisa estar logado!")
        return

    try: # <--- Começa o bloco de tentativa
        user_id = st.session_state.user.id
        dados = {
            "id": user_id,
            "nome_empresa": st.session_state.get('nome_empresa', ''),
            "crt": st.session_state.get('crt', ''),
            "telefone": st.session_state.get('telefone', ''),
            "cnpj": st.session_state.get('cnpj', ''),
            "endereco": st.session_state.get('endereco', ''),
            "email_contato": st.session_state.get('email_contato', ''),
            "email": st.session_state.user.email
        }
        supabase.table("profiles").upsert(dados).execute()
        st.success("✅ Dados sincronizados!")
        
    except Exception as e: # <--- FALTAVA ISSO AQUI!
        st.error(f"Erro ao salvar: {e}")

# --- 4. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'user' not in st.session_state: st.session_state.user = None
if 'dados_cargas' not in st.session_state:
    st.session_state.dados_cargas = pd.DataFrame([{
        "Cômodo": "Sala", "Tipo": "Social", "Área (m²)": 0.0, "Perímetro (m)": 0.0, 
        "TUG (Qtd)": 0, "TUE (Watts)": 0, "Iluminação (VA)": 0, "Lâmpadas": 0
    }])

# --- 5. TELA DE ACESSO ---
if not st.session_state.logado:
    st.title("⚡ VoltSpec Pro - Portal do Técnico")
    tab_login, tab_create = st.tabs(["🔐 Login", "📝 Criar Conta"])
    
    with tab_login:
        email_in = st.text_input("E-mail", key="li_email")
        pass_in = st.text_input("Senha", type="password", key="li_pass")
        if st.button("Acessar Sistema"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email_in, "password": pass_in})
                if res.user:
                    st.session_state.user = res.user
                    st.session_state.logado = True
                    carregar_perfil_supabase()
                    st.rerun()
            except Exception as e:
                st.error(f"Acesso negado: Credenciais inválidas ou e-mail não confirmado.")
            
    with tab_create:
        new_email = st.text_input("Novo E-mail", key="su_email")
        new_pass = st.text_input("Nova Senha", type="password", key="su_pass")
        if st.button("Cadastrar como Técnico Pro"):
            try:
                res = supabase.auth.sign_up({"email": new_email, "password": new_pass})
                if res.user: 
                    st.success("Conta criada! Se o login não funcionar, confirme o e-mail ou peça ao admin para liberar.")
            except Exception as ex: st.error(f"Erro no cadastro: {ex}")
    st.stop()

# --- 6. ÁREA DO SISTEMA ---
st.sidebar.title("VoltSpec Pro ⚡")
st.sidebar.write(f"Conectado: {st.session_state.user.email}")

if st.sidebar.button("Sair / Logout"):
    st.session_state.logado = False
    st.session_state.user = None
    st.rerun()

aba = st.radio("Módulo:", ["⚙️ Perfil", "🏠 Cargas", "📐 Dimensionador", "💰 Orçamentos", "📦 Materiais", "🛒 Produtos"], horizontal=True)

# --- MÓDULO PERFIL ---
if aba == "⚙️ Perfil":
    st.header("⚙️ Perfil do Técnico")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Sincronizar da Nuvem", use_container_width=True):
            carregar_perfil_supabase()
            st.rerun()
    with col2:
        if st.button("💾 Salvar na Nuvem", use_container_width=True):
            salvar_perfil_supabase()

    st.divider()
    with st.expander("📝 Editar Informações", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.nome_empresa = st.text_input("Empresa/Nome:", value=st.session_state.get('nome_empresa', ''))
            st.session_state.crt = st.text_input("Registro (CRT/CFT):", value=st.session_state.get('crt', ''))
            st.session_state.telefone = st.text_input("WhatsApp:", value=st.session_state.get('telefone', ''))
        with c2:
            st.session_state.cnpj = st.text_input("CNPJ/CPF:", value=st.session_state.get('cnpj', ''))
            st.session_state.email_contato = st.text_input("E-mail Contato:", value=st.session_state.get('email_contato', st.session_state.user.email))
            st.session_state.endereco = st.text_input("Endereço:", value=st.session_state.get('endereco', 'Araxá - MG'))
# --- MÓDULO: QUADRO DE CARGAS  ---
elif aba == "🏠 Cargas":
    st.header("📋 Dimensionamento de Cargas (NBR 5410)")

    # 1. ESTRUTURA DE DADOS (Garante colunas e tipos corretos)
    colunas_obrigatorias = ["Cômodo", "Tipo", "Área (m²)", "Perímetro (m)", "Iluminação (VA/Lâmp.)", "TUG (Qtd)", "Potência TUG (VA)", "TUE (Watts)"]
    
    if 'dados_cargas' not in st.session_state or "Iluminação (VA/Lâmp.)" not in st.session_state.dados_cargas.columns:
        st.session_state.dados_cargas = pd.DataFrame({
            "Cômodo": ["Sala", "Cozinha", "Banheiro"],
            "Tipo": ["Social", "Molhada", "Banheiro"],
            "Área (m²)": [0.0]*3, "Perímetro (m)": [0.0]*3,
            "Iluminação (VA/Lâmp.)": ["0 VA (0 pt)"]*3,
            "TUG (Qtd)": [0]*3,
            "Potência TUG (VA)": [0.0]*3,
            "TUE (Watts)": [0.0]*3
        })

    # 2. INTERFACE DA PLANILHA (Permite adicionar linhas dinamicamente)
    st.subheader("📝 1. Entrada de Dados")
    df_input = st.data_editor(
        st.session_state.dados_cargas,
        num_rows="dynamic", # Permite que você clique no "+" para adicionar banheiros novos
        use_container_width=True,
        key="editor_voltspec_v22"
    )

    # 3. PROCESSO DE CÁLCULO E RECONHECIMENTO AUTOMÁTICO
    if st.button("⚡ Calcular e Gerar Distribuição", type="primary", use_container_width=True):
        df_calc = df_input.copy()
        
        for i, r in df_calc.iterrows():
            try:
                # Normaliza os textos para busca (remove espaços e deixa minúsculo)
                nome_comodo = str(r["Cômodo"]).strip().lower()
                tipo_comodo = str(r["Tipo"]).strip().lower()
                
                a = float(r["Área (m²)"])
                p = float(r["Perímetro (m)"])

                # --- IDENTIFICAÇÃO DE BANHEIRO / ÁREA MOLHADA ---
                # Verifica se a palavra 'banheiro' ou 'wc' está em qualquer uma das colunas
                is_banheiro = any(x in nome_comodo or x in tipo_comodo for x in ["banheiro", "wc", "suíte", "suite"])
                is_molhada = is_banheiro or any(x in tipo_comodo or x in nome_comodo for x in ["cozinha", "serviço", "lavanderia", "copa"])

                # --- 1. ILUMINAÇÃO ---
                pot_ilum = 100 if a <= 6 else 100 + (math.floor((a-6)/4)*60)
                qtd_lamp = math.ceil(a / 4) if a > 0 else 0
                df_calc.at[i, "Iluminação (VA/Lâmp.)"] = f"{pot_ilum} VA ({qtd_lamp} pt)"
                
                # --- 2. TUGS (Tomadas) ---
                div = 3.5 if is_molhada else 5.0
                qtd_tugs = math.ceil(p / div)
                
                # Garantia NBR 5410: Mínimo 1 tomada em banheiros/cozinhas/salas
                if a > 0: qtd_tugs = max(qtd_tugs, 1)
                
                df_calc.at[i, "TUG (Qtd)"] = qtd_tugs
                
                if is_molhada:
                    # Regra: 3 primeiras de 600VA, resto 100VA
                    df_calc.at[i, "Potência TUG (VA)"] = (min(qtd_tugs, 3) * 600) + (max(0, qtd_tugs - 3) * 100)
                else:
                    df_calc.at[i, "Potência TUG (VA)"] = qtd_tugs * 100

                # --- 3. TUE (Automação de Chuveiro) ---
                # Se for identificado como banheiro e o campo TUE estiver zerado ou vazio
                if is_banheiro and (pd.isna(r["TUE (Watts)"]) or float(r["TUE (Watts)"]) == 0):
                    df_calc.at[i, "TUE (Watts)"] = 5500.0 # Padrão Chuveiro
                    
            except Exception as e:
                continue
        
        st.session_state.dados_cargas = df_calc
        st.session_state['qdc_pronto'] = True
        st.rerun()

    # 4. EXIBIÇÃO DO QUADRO DE DISTRIBUIÇÃO (QDC)
    if st.session_state.get('qdc_pronto', False):
        st.divider()
        st.subheader("⚡ 2. Quadro de Distribuição Sugerido")
        
        df_final = st.session_state.dados_cargas
        circuitos = []
        
        def extrair_va(texto):
            try: return float(str(texto).split(" ")[0])
            except: return 0.0

        # --- C01: ILUMINAÇÃO ---
        total_va_ilum = sum(df_final["Iluminação (VA/Lâmp.)"].apply(extrair_va))
        if total_va_ilum > 0:
            ib = total_va_ilum / 127
            circuitos.append({
                "Circuito": "C01", "Descrição": "Iluminação Geral",
                "Potência": f"{total_va_ilum:.0f} VA", "Corrente (Ib)": f"{ib:.2f} A",
                "Cabo": "1.5 mm²", "Disjuntor": "10 A"
            })

        # --- CIRCUITOS DE TUGS ---
        total_tug = df_final["Potência TUG (VA)"].sum()
        if total_tug > 0:
            ib_tug = total_tug / 127
            num_ckts = math.ceil(ib_tug / 16)
            for n in range(num_ckts):
                circuitos.append({
                    "Circuito": f"C{len(circuitos)+1:02d}", "Descrição": f"TUGs - Grupo {n+1}",
                    "Potência": f"{total_tug/num_ckts:.0f} VA", "Corrente (Ib)": f"{(ib_tug/num_ckts):.2f} A",
                    "Cabo": "2.5 mm²", "Disjuntor": "20 A"
                })

        # --- CIRCUITOS DE TUES (Individuais) ---
        for _, r in df_final.iterrows():
            tue = float(r.get("TUE (Watts)") or 0)
            if tue > 0:
                v_tue = 220 if tue >= 4000 else 127
                ib_tue = tue / v_tue
                cabo = 2.5 if ib_tue <= 21 else (4.0 if ib_tue <= 28 else 6.0)
                circuitos.append({
                    "Circuito": f"C{len(circuitos)+1:02d}", "Descrição": f"TUE - {r['Cômodo']}",
                    "Potência": f"{tue:.0f} W", "Corrente (Ib)": f"{ib_tue:.2f} A",
                    "Cabo": f"{cabo} mm²", "Disjuntor": f"{math.ceil(ib_tue/5)*5 + 5} A"
                })

        st.dataframe(pd.DataFrame(circuitos), use_container_width=True)
# --- MÓDULO: DIMENSIONADOR (CÉREBRO NBR 5410) ---
elif aba == "📐 Dimensionador":
    st.header("📐 Dimensionamento Profissional (NBR 5410)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📥 Dados de Entrada")
        p_watts = st.number_input("Potência da Carga (Watts):", min_value=0.0, value=1200.0)
        tensao = st.selectbox("Tensão (V):", [127, 220])
        distancia = st.number_input("Comprimento do Circuito (metros):", min_value=1.0, value=10.0)
        
        st.divider()
        st.write("**Fatores de Correção:**")
        agrupamento = st.slider("Nº de circuitos no mesmo eletroduto:", 1, 6, 1)
        # Tabela 42 da NBR 5410 (Fator de Agrupamento)
        fator_ag = {1: 1.0, 2: 0.80, 3: 0.70, 4: 0.65, 5: 0.60, 6: 0.57}.get(agrupamento)

    with col2:
        st.subheader("📊 Resultado Técnico")
        
        # 1. Cálculo da Corrente de Projeto (Ib)
        ib = p_watts / tensao
        
        # 2. Cálculo da Corrente Corrigida (Iz) -> Onde a norma atua
        iz_necessaria = ib / fator_ag
        
        # 3. Tabela de Capacidade de Condução (Método B1 - Cabos de Cobre/PVC)
        # Bitola: Amperagem Máxima
        tabela_condutores = {
            1.5: 17.5,
            2.5: 24.0,
            4.0: 32.0,
            6.0: 41.0,
            10.0: 57.0,
            16.0: 76.0
        }
        
        bitola_escolhida = 1.5
        for bitola, capacidade in tabela_condutores.items():
            if capacidade >= iz_necessaria:
                bitola_escolhida = bitola
                break
        
        # 4. Verificação de Queda de Tensão (Máximo 4% para residências)
        # Fórmula: ΔU = (2 * L * Ib * ρ) / S
        rho = 0.0172 # Resistividade do cobre
        queda_v = (2 * distancia * ib * rho) / bitola_escolhida
        percentual_queda = (queda_v / tensao) * 100
        
        # Exibição dos cards
        st.metric("Corrente de Projeto (Ib)", f"{ib:.2f} A")
        st.metric("Corrente Corrigida (Iz)", f"{iz_necessaria:.2f} A", help="Corrente considerando o aquecimento por agrupamento")
        
        st.success(f"⚡ Bitola Sugerida: **{bitola_escolhida} mm²**")
        
        if percentual_queda <= 4.0:
            st.info(f"✅ Queda de Tensão: {percentual_queda:.2f}% (Dentro do limite de 4%)")
        else:
            st.error(f"⚠️ Queda de Tensão Alta: {percentual_queda:.2f}%! Aumente a bitola manualmente.")

    st.divider()
    st.caption("Nota: Cálculos baseados na NBR 5410:2004, Método de Instalação B1 (Eletroduto embutido em alvenaria).")
# --- MÓDULO: ORÇAMENTOS E MATERIAIS (ITENS COMPLETOS) ---
elif aba in ["💰 Orçamentos", "📦 Materiais"]:
    st.header(f"📊 {aba} Profissional")
    cli_nome = st.text_input("Cliente / Obra:", "Cliente Araxá", key=f"cli_nome_v11_{aba}")
    
    if aba == "💰 Orçamentos":
        # LISTA DE SERVIÇOS TÉCNICOS DETALHADA
        itens = [
            {"Descrição": "Ponto de Tomada / Interruptor (Instalação)", "Qtd": 0, "Preço": 85.0},
            {"Descrição": "Ponto de Iluminação (Luminária/Plafon)", "Qtd": 0, "Preço": 75.0},
            {"Descrição": "Montagem de Quadro de Distribuição (até 12 disj.)", "Qtd": 0, "Preço": 450.0},
            {"Descrição": "Montagem de Quadro de Distribuição (acima 12 disj.)", "Qtd": 0, "Preço": 650.0},
            {"Descrição": "Padrão CEMIG Monofásico (Instalação)", "Qtd": 0, "Preço": 850.0},
            {"Descrição": "Padrão CEMIG Trifásico (Instalação)", "Qtd": 0, "Preço": 1350.0},
            {"Descrição": "Instalação de Chuveiro / Torneira Elétrica", "Qtd": 0, "Preço": 110.0},
            {"Descrição": "Instalação de Dispositivo DR / DPS (Extra)", "Qtd": 0, "Preço": 65.0},
            {"Descrição": "Passagem de Fiação (por circuito/m)", "Qtd": 0, "Preço": 25.0},
            {"Descrição": "Manutenção Preventiva / Reaperto de Bornes", "Qtd": 0, "Preço": 250.0},
            {"Descrição": "Laudo Técnico de Conformidade / Visita", "Qtd": 0, "Preço": 300.0}
        ]
    else:
        # LISTA DE MATERIAIS ELÉTRICOS INDISPENSÁVEIS
        itens = [
            {"Descrição": "Cabo Flexível 2,5mm 750V (Rolo 100m)", "Qtd": 0, "Preço": 285.0},
            {"Descrição": "Cabo Flexível 4,0mm 750V (Rolo 100m)", "Qtd": 0, "Preço": 420.0},
            {"Descrição": "Cabo Flexível 6,0mm 750V (Rolo 100m)", "Qtd": 0, "Preço": 645.0},
            {"Descrição": "Disjuntor DIN Monopolar (10A a 32A)", "Qtd": 0, "Preço": 19.90},
            {"Descrição": "Dispositivo DR (IDR) Bipolar 40A", "Qtd": 0, "Preço": 189.0},
            {"Descrição": "Dispositivo DPS 20kA 275V", "Qtd": 0, "Preço": 58.0},
            {"Descrição": "Fita Isolante 20m (Antichama)", "Qtd": 0, "Preço": 18.50},
            {"Descrição": "Barramento Pente Bifásico (1 Metro)", "Qtd": 0, "Preço": 55.0},
            {"Descrição": "Caixa de Passagem 4x2 (Unidade)", "Qtd": 0, "Preço": 3.50},
            {"Descrição": "Eletroduto Corrugado 3/4 (Rolo 50m)", "Qtd": 0, "Preço": 75.0},
            {"Descrição": "Conector Wago (Kit 10 un)", "Qtd": 0, "Preço": 45.0}
        ]
    
    # Editor de dados com chave única para evitar erro de duplicidade
    df_final = st.data_editor(
        pd.DataFrame(itens), 
        num_rows="dynamic", 
        use_container_width=True, 
        key=f"ed_v11_{aba}"
    )
    
    total_val = (df_final["Qtd"] * df_final["Preço"]).sum()
    st.subheader(f"Total Estimado: R$ {total_val:,.2f}")
    
    # Botão de PDF atualizado
    if st.button("📄 Gerar Orçamento em PDF", key=f"btn_pdf_pro_{aba}"):
        pdf = FPDF()
        pdf.add_page()
        
        # 1. LIMPEZA DE TEXTO (Remove emojis para não travar o FPDF)
        def limpar_texto(txt):
            # Remove emojis comuns e garante compatibilidade latin-1
            return str(txt).replace("💰", "").replace("📦", "").replace("🏠", "").replace("📐", "").replace("⚙️", "").strip()

        nome_modulo = limpar_texto(aba).upper()
        empresa = limpar_texto(st.session_state.get('nome_empresa', 'VOLTSPEC PRO'))
        tecnico_crt = limpar_texto(st.session_state.get('crt', 'TÉCNICO RESPONSÁVEL'))
        contato_fixo = limpar_texto(f"Tel: {st.session_state.get('telefone', '')} | {st.session_state.get('email_contato', '')}")
        local_obra = limpar_texto(st.session_state.get('endereco', 'Araxá - MG'))

        # 2. CABEÇALHO COM DESIGN (RETÂNGULO DE DESTAQUE)
        pdf.set_fill_color(245, 245, 245)
        pdf.rect(10, 10, 190, 35, 'F')
        
        # Nome da Empresa / Técnico
        pdf.set_font("Arial", "B", 16)
        pdf.set_xy(10, 15)
        pdf.cell(190, 8, empresa.encode('latin-1', 'ignore').decode('latin-1'), 0, 1, "C")
        
        # Dados do CRT e Contatos
        pdf.set_font("Arial", "B", 9)
        pdf.cell(190, 5, tecnico_crt.encode('latin-1', 'ignore').decode('latin-1'), 0, 1, "C")
        pdf.set_font("Arial", "", 9)
        pdf.cell(190, 5, contato_fixo.encode('latin-1', 'ignore').decode('latin-1'), 0, 1, "C")
        pdf.cell(190, 5, local_obra.encode('latin-1', 'ignore').decode('latin-1'), 0, 1, "C")
        
        # 3. TÍTULO DO DOCUMENTO E CLIENTE
        pdf.ln(15)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, f"PROPOSTA COMERCIAL: {nome_modulo}", "B", 1, "L")
        
        pdf.ln(5)
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, f"CLIENTE: {limpar_texto(cli_nome).upper()}", 0, 1)
        pdf.cell(0, 8, f"DATA: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
        
        pdf.ln(5)
        
        # 4. TABELA DE ITENS (CABEÇALHO)
        pdf.set_fill_color(30, 41, 59) # Cor escura profissional
        pdf.set_text_color(255, 255, 255) # Texto branco
        pdf.set_font("Arial", "B", 10)
        pdf.cell(110, 8, " Descrição do Item/Serviço", 1, 0, "L", True)
        pdf.cell(20, 8, "Qtd", 1, 0, "C", True)
        pdf.cell(30, 8, "Unit. (R$)", 1, 0, "C", True)
        pdf.cell(30, 8, "Subtotal", 1, 1, "C", True)
        
        # Itens da Tabela
        pdf.set_text_color(0, 0, 0) # Volta texto para preto
        pdf.set_font("Arial", "", 10)
        for _, r in df_final.iterrows():
            if r["Qtd"] > 0:
                desc = limpar_texto(r['Descrição'])
                sub = r["Qtd"] * r["Preço"]
                pdf.cell(110, 8, f" {desc}", 1)
                pdf.cell(20, 8, f"{r['Qtd']}", 1, 0, "C")
                pdf.cell(30, 8, f"{r['Preço']:.2f}", 1, 0, "C")
                pdf.cell(30, 8, f"{sub:.2f}", 1, 1, "C")
        
        # 5. TOTAL E RODAPÉ TÉCNICO
        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"VALOR TOTAL: R$ {total_val:.2f}", 0, 1, "R")
        
        pdf.ln(20)
        pdf.set_font("Arial", "I", 8)
        obs = (
            "Observações: Este documento tem caráter de orçamento técnico. "
            "A execução dos serviços seguirá as normas da NBR 5410. "
            "Validade desta proposta: 10 dias."
        )
        pdf.multi_cell(0, 5, obs.encode('latin-1', 'ignore').decode('latin-1'), 0, "C")
        
       
      # Converte o bytearray do FPDF para o formato de bytes que o Streamlit aceita
        pdf_output = pdf.output()
        pdf_bytes = bytes(pdf_output) 
        
        st.download_button(
            label="⬇️ Baixar Proposta Técnica PDF",
            data=pdf_bytes, 
            file_name=f"Orcamento_{limpar_texto(cli_nome).replace(' ', '_')}.pdf",
            mime="application/pdf",
            key=f"dl_final_pro_{aba}"
        )
# --- MÓDULO: PRODUTOS (VITRINE COM LINKS DO MERCADO LIVRE) ---
elif aba == "🛒 Produtos":
    st.header("🛒 Recomendação de Materiais (Mercado Livre)")
    st.write("Selecione os componentes abaixo para compra direta nos melhores fornecedores:")

    # Lista de Produtos - Você pode alterar os links e as imagens aqui
    # Dica: No Mercado Livre, clique com o botão direito na imagem e vá em "Copiar endereço da imagem"
    produtos = [
        {
            "nome": "Jogo Chaves Fenda E Philips Isoladas Eletricista Imã 6 Peças",
            "img": "https://http2.mlstatic.com/D_NQ_NP_2X_701755-MLB85959666529_062025-F.webp",
            "link": "https://meli.la/2xLSiQJ",
          
        },
        {
            "nome": "Alicate Crimpar Prensa Terminais 1200 Ilhós Tubular Cietec",
            "img": "https://http2.mlstatic.com/D_NQ_NP_2X_928036-MLA99440131490_112025-F.webp",
            "link": "https://meli.la/247XSK7",
            
        },
        {
            "nome": "Alicate Decapador Vonder Fios Eletricista 0.2mm² 6.0mm² Cortador E Crimpador Profissional 8 Polegadas 203mm - Preto e Amarelo 32g",
            "img": "https://http2.mlstatic.com/D_NQ_NP_2X_608489-MLA99480826142_112025-F.webp",
            "link": "https://meli.la/2L47LTv",
            
        },
        {
            "nome": "Bolsa Ferramentas Grande Reforçada Eletricista Mochila Lona Cor Amarelo",
            "img": "https://http2.mlstatic.com/D_NQ_NP_2X_947240-MLA99992405049_112025-F.webp",
            "link": "https://meli.la/1E4on12",
           
        },
        {
            "nome": "Capacete Segurança 3m H700 C/ Jugular Eletricista Engenheiro",
            "img": "https://http2.mlstatic.com/D_NQ_NP_2X_626460-MLB94142486331_102025-F-capacete-seguranca-3m-h700-c-jugular-eletricista-engenheiro.webp",
            "link": "https://meli.la/1rXP7Yd",
            
        },
        {
            "nome": "Guia Passa Fio 20m Cabo De Energia Quadro Elétrico - Vonder",
            "img": "https://http2.mlstatic.com/D_NQ_NP_2X_994783-MLB88833382323_072025-F.webp",
            "link": "https://meli.la/2CRuen3",
            
        }
    ]

    # Criando a grade de exibição (3 colunas por linha)
    cols = st.columns(3)
    
    for i, p in enumerate(produtos):
        with cols[i % 3]:
            # --- TRATAMENTO DE SEGURANÇA PARA AS CHAVES ---
            # Se a chave 'preco' não existir, ele usa 'Preço não disponível'
            nome_prod = p.get('nome', 'Produto sem nome')
            preco_prod = p.get('preco', 'Sob consulta')
            link_prod = p.get('link', '#')
            img_prod = p.get('img', 'https://via.placeholder.com/140') # Imagem padrão caso falhe

            # Container do Produto em HTML/CSS
            st.markdown(f"""
                <div style="
                    border: 1px solid #e0e0e0; 
                    padding: 20px; 
                    border-radius: 12px; 
                    background-color: white; 
                    margin-bottom: 25px; 
                    text-align: center;
                    box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
                    transition: transform 0.2s;
                ">
                    <img src="{img_prod}" style="width: 140px; height: 140px; object-fit: contain; margin-bottom: 15px;">
                    <h4 style="color: #1e293b; font-size: 15px; height: 40px; overflow: hidden; margin-bottom: 10px;">
                        {nome_prod}
                    </h4>
                    <p style="color: #0284c7; font-weight: bold; font-size: 20px; margin-bottom: 15px;">
                        {preco_prod}
                    </p>
                    <a href="{link_prod}" target="_blank" style="text-decoration: none;">
                        <button style="
                            width: 100%; 
                            background-color: #fff159; 
                            color: #2d3277; 
                            border: none; 
                            padding: 12px; 
                            border-radius: 6px; 
                            font-weight: bold; 
                            cursor: pointer;
                            font-size: 14px;
                        ">
                            Ver no Mercado Livre 🚀
                        </button>
                    </a>
                </div>
            """, unsafe_allow_html=True)