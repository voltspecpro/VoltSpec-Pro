import streamlit as st
import pandas as pd
import math
from datetime import datetime
from fpdf import FPDF
from supabase import create_client, Client
import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
 
# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="VoltSpec Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)
 
st.markdown("""
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="application-name" content="VoltSpec Pro">
    <meta name="apple-mobile-web-app-title" content="VoltSpec Pro">
    <meta name="theme-color" content="#000000">
    <meta name="msapplication-navbutton-color" content="#000000">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    """, unsafe_allow_html=True)
 
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
 
# --- 2. CONEXÃO COM BANCO (SUPABASE) ---
URL_SUPA = st.secrets.get("SUPABASE_URL", "")
KEY_SUPA = st.secrets.get("SUPABASE_KEY", "")
 
def init_connection():
    try:
        return create_client(URL_SUPA, KEY_SUPA)
    except Exception as e:
        st.error(f"❌ Erro na conexão com o Supabase: {e}")
        return None
 
supabase = init_connection()
 
if supabase is None:
    st.warning("⚠️ Aplicativo sem conexão com o banco de dados. Algumas funções estarão indisponíveis.")
 
# --- FUNÇÃO AUXILIAR: cliente autenticado com token da sessão ---
def get_supabase_autenticado():
    try:
        session = st.session_state.get('session')
        if session and session.access_token:
            supabase.auth.set_session(session.access_token, session.refresh_token)
    except Exception:
        pass
    return supabase
 
# --- 3. FUNÇÕES DE SUPORTE (PDF E LIMPEZA) ---
 
def limpar_texto(txt):
    if not txt:
        return ""
    return str(txt).encode('latin-1', 'ignore').decode('latin-1').replace("²", "2").strip()
 
def montar_cabecalho_pdf(pdf):
    p = st.session_state.get('perfil', {})
    
    emp      = limpar_texto(p.get('nome_empresa', '')) or 'VoltSpec Pro'
    crt      = limpar_texto(p.get('crt', ''))
    tel      = limpar_texto(p.get('telefone', ''))
    cnpj     = limpar_texto(p.get('cnpj', ''))
    cidade   = limpar_texto(p.get('endereco', ''))
    email    = limpar_texto(p.get('email_contato', ''))
 
    # Fundo escuro
    pdf.set_fill_color(30, 41, 59)
    pdf.rect(0, 0, 210, 50, 'F')
    pdf.set_text_color(255, 255, 255)
 
    # Nome da empresa (grande)
    pdf.set_font("Arial", "B", 16)
    pdf.set_xy(0, 6)
    pdf.cell(210, 10, emp.upper(), align="C", ln=True)
 
    # Linha 1: CRT e Telefone
    linha1 = ""
    if crt:  linha1 += f"Reg.: {crt}"
    if tel:  linha1 += f"  |  Tel: {tel}"
    if linha1:
        pdf.set_font("Arial", "", 9)
        pdf.cell(210, 6, linha1.strip(), align="C", ln=True)
 
    # Linha 2: CNPJ e Cidade
    linha2 = ""
    if cnpj:   linha2 += f"CNPJ: {cnpj}"
    if cidade: linha2 += f"  |  {cidade}"
    if linha2:
        pdf.set_font("Arial", "", 9)
        pdf.cell(210, 6, linha2.strip(), align="C", ln=True)
 
    # Linha 3: E-mail
    if email:
        pdf.set_font("Arial", "", 9)
        pdf.cell(210, 6, email, align="C", ln=True)
 
    # Volta cor de texto para preto
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)
 
def gerar_pdf_universal(titulo, df_dados, colunas_w, headers):
    """Gera PDF para Orçamentos ou Materiais — com cabeçalho do perfil"""
    pdf = FPDF()
    pdf.add_page()
 
    montar_cabecalho_pdf(pdf)
 
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"RELATORIO: {limpar_texto(titulo)}", "B", 1, "L")
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 8, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, "R")
    pdf.ln(5)
 
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", "B", 9)
    for i, h in enumerate(headers):
        pdf.cell(colunas_w[i], 8, limpar_texto(h), 1, 0, "C", True)
    pdf.ln()
 
    pdf.set_font("Arial", "", 8)
    total = 0
    for _, r in df_dados.iterrows():
        if r.get("Qtd", 0) > 0:
            sub = r["Qtd"] * r["Preco"]
            total += sub
            pdf.cell(colunas_w[0], 7, limpar_texto(r["Descricao"]), 1)
            pdf.cell(colunas_w[1], 7, str(r["Qtd"]), 1, 0, "C")
            pdf.cell(colunas_w[2], 7, f"{r['Preco']:.2f}", 1, 0, "C")
            pdf.cell(colunas_w[3], 7, f"{sub:.2f}", 1, 1, "C")
 
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"TOTAL: R$ {total:.2f}", 0, 1, "R")
 
    return pdf.output(dest="S").encode("latin-1")
 
# --- 4. FUNÇÕES DE BANCO DE DADOS ---

def carregar_perfil_supabase():
    # ... (mantenha a verificação inicial)
    try:
        cliente = get_supabase_autenticado()
        res = cliente.table("profiles").select("*").eq("id", st.session_state.user.id).execute()
        if res.data:
            d = res.data[0]
            st.session_state.perfil['nome_empresa']  = d.get('nome_empresa', '')
            st.session_state.perfil['crt']           = d.get('crt', '')
            st.session_state.perfil['telefone']      = d.get('telefone', '')
            st.session_state.perfil['cnpj']          = d.get('cnpj', '')
            st.session_state.perfil['endereco']      = d.get('endereco_comercial', '')
            st.session_state.perfil['email_contato'] = d.get('email', '')
    except Exception as e:
        st.warning(f"⚠️ Não foi possível carregar o perfil: {e}")

def salvar_perfil_supabase():
    # ... (mantenha a verificação inicial)
    try:
        cliente = get_supabase_autenticado()
        dados = {
            "id":                 st.session_state.user.id,
            "nome_empresa":       st.session_state.perfil.get('nome_empresa', ''),
            "crt":                st.session_state.perfil.get('crt', ''),
            "telefone":           st.session_state.perfil.get('telefone', ''),
            "cnpj":               st.session_state.perfil.get('cnpj', ''),
            "email":              st.session_state.user.email,
            "endereco_comercial": st.session_state.perfil.get('endereco', '')
        }
        cliente.table("profiles").upsert(dados).execute()
        st.success("✅ Sincronizado!")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
# --- 5. ESTADO INICIAL ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'session' not in st.session_state:
    st.session_state.session = None
if 'perfil_carregado' not in st.session_state:
    st.session_state.perfil_carregado = False
 
if 'dados_cargas' not in st.session_state:
    st.session_state.dados_cargas = pd.DataFrame([{
        "Comodo": "Sala", "Area (m2)": 0.0, "Perimetro (m)": 0.0,
        "Iluminacao (VA)": "-", "TUG (Qtd)": 0,
        "Potencia TUG (VA)": 0.0, "TUE (Watts)": 0.0
    }])
 
if 'lista_circuitos' not in st.session_state:
    st.session_state.lista_circuitos = []
if 'resumo_materiais' not in st.session_state:
    st.session_state.resumo_materiais = []
 
if 'perfil' not in st.session_state:
    st.session_state.perfil = {
        'nome_empresa': '', 'crt': '', 'telefone': '', 'cnpj': '', 'endereco': '', 'email_contato': ''
    }
 # LÁ EMBAIXO NO BOTÃO DE SAIR:
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.session_state.user   = None
    st.session_state.session = None
    st.session_state.perfil_carregado = False
    st.session_state.perfil = {
        'nome_empresa': '', 'crt': '', 'telefone': '', 'cnpj': '', 'endereco': '', 'email_contato': ''
    }
    st.rerun()

# --- 6. TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("⚡ VoltSpec Pro")
    t1, t2 = st.tabs(["Login", "Criar Conta"])
    with t1:
        em = st.text_input("E-mail")
        pw = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if supabase is None:
                st.error("❌ Sem conexão com o banco de dados.")
            else:
                try:
                    res = supabase.auth.sign_in_with_password({"email": em, "password": pw})
                    if res.user:
                        st.session_state.user    = res.user
                        st.session_state.session = res.session
                        st.session_state.logado  = True
                        st.session_state.perfil_carregado = False
                        st.rerun()
                except Exception as e:
                    st.error(f"Falha no login: {e}")
    with t2:
        nem = st.text_input("Novo E-mail")
        npw = st.text_input("Nova Senha", type="password")
        if st.button("Cadastrar"):
            if supabase is None:
                st.error("❌ Sem conexão com o banco de dados.")
            else:
                try:
                    supabase.auth.sign_up({"email": nem, "password": npw})
                    st.success("Sucesso! Verifique seu e-mail.")
                except Exception as e:
                    st.error(f"Erro no cadastro: {e}")
    st.stop()
 
# --- CARREGA PERFIL APÓS LOGIN (uma única vez por sessão) ---
if st.session_state.logado and not st.session_state.perfil_carregado:
    carregar_perfil_supabase()
    st.session_state.perfil_carregado = True
 
# --- 7. SISTEMA PRINCIPAL ---
st.sidebar.title("VoltSpec Pro ⚡")
if st.sidebar.button("Sair", key="btn_sair_logoff"): # Adicionei a key aqui
    st.session_state.logado = False
    st.session_state.user   = None
    st.session_state.session = None
    st.session_state.perfil_carregado = False
    # Reinicia o dicionário de perfil para não sobrar rastro de dados
    st.session_state.perfil = {
        'nome_empresa': '', 'crt': '', 'telefone': '', 'cnpj': '', 
        'endereco': '', 'email_contato': ''
    }
    st.rerun()
 
aba = st.radio("Navegação:", ["⚙️ Perfil", "🏠 Cargas", "💡 Luminotecnica", "📐 Dimensionador", "💰 Orçamentos", "📦 Materiais", "🛒 Produtos"], horizontal=True)
 
# --- MÓDULO PERFIL ---
if aba == "⚙️ Perfil":
    st.header("⚙️ Configurações do Técnico")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.perfil['nome_empresa'] = st.text_input("Empresa:", value=st.session_state.perfil.get('nome_empresa', ''))
        st.session_state.perfil['crt']          = st.text_input("CRT/CFT:", value=st.session_state.perfil.get('crt', ''))
        st.session_state.perfil['telefone']     = st.text_input("WhatsApp:", value=st.session_state.perfil.get('telefone', ''))
    with c2:
        st.session_state.perfil['cnpj']          = st.text_input("CNPJ:", value=st.session_state.perfil.get('cnpj', ''))
        st.session_state.perfil['email_contato'] = st.text_input("E-mail Profissional:", value=st.session_state.perfil.get('email_contato', ''))
        st.session_state.perfil['endereco']      = st.text_input("Cidade/UF:", placeholder="Ex: Araxá - MG", value=st.session_state.perfil.get('endereco', ''))

    if st.button("💾 Salvar na Nuvem"):
        salvar_perfil_supabase()
# --- MÓDULO CARGAS ---
elif aba == "🏠 Cargas":
    st.header("📋 Dimensionamento Profissional (NBR 5410 + Materiais)")
 
    with st.expander("🔌 Configuração da Rede e Concessionária", expanded=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            concessionaria = st.selectbox("Selecione a Concessionária:",
                                          ["CEMIG (MG)", "CPFL (SP)", "ENEL (RJ/SP)", "EQUATORIAL", "Outra (Manual)"])
        with col_c2:
            tensao_fase = st.selectbox("Tensão Fase-Neutro (V):", [127, 220], index=0)
 
    if st.session_state.dados_cargas.columns.tolist() != ["Comodo", "Area (m2)", "Perimetro (m)", "Iluminacao (VA)", "TUG (Qtd)", "Potencia TUG (VA)", "TUE (Watts)"]:
        st.session_state.dados_cargas = pd.DataFrame({
            "Comodo": ["Sala", "Cozinha", "Quarto 1", "Quarto 2", "Banheiro"],
            "Area (m2)": [15.0, 10.0, 12.0, 10.0, 4.5],
            "Perimetro (m)": [16.0, 13.0, 14.0, 13.0, 9.0],
            "Iluminacao (VA)": ["-", "-", "-", "-", "-"],
            "TUG (Qtd)": [0, 0, 0, 0, 0],
            "Potencia TUG (VA)": [0.0, 0.0, 0.0, 0.0, 0.0],
            "TUE (Watts)": [0.0, 0.0, 0.0, 0.0, 5500.0]
        })
 
    st.subheader("1. Entrada de Dados e Medidas")
    df_editor = st.data_editor(
        st.session_state.dados_cargas,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_cargas_v1"
    )
 
    if st.button("⚡ Calcular Projeto e Dimensionar Circuitos", type="primary", use_container_width=True):
        df_calc = df_editor.copy()
        novos_circuitos = []
        pot_ilum_total = 0
        pot_tug_total = 0
 
        cabos = {
            "1.5mm2":  {"Fase": 0, "Neutro": 0, "Terra": 0},
            "2.5mm2":  {"Fase": 0, "Neutro": 0, "Terra": 0},
            "4.0mm2":  {"Fase": 0, "Neutro": 0, "Terra": 0},
            "6.0mm2":  {"Fase": 0, "Neutro": 0, "Terra": 0},
            "10.0mm2": {"Fase": 0, "Neutro": 0, "Terra": 0},
        }
 
        for i, r in df_calc.iterrows():
            try:
                a    = float(r["Area (m2)"])
                p    = float(r["Perimetro (m)"])
                nome = str(r["Comodo"]).lower()
 
                va_ilum = 100 if a <= 6 else 100 + (math.floor((a - 6) / 4) * 60)
                qtd_lamp = max(math.ceil(va_ilum / 100), 1)
                df_calc.at[i, "Iluminacao (VA)"] = f"{qtd_lamp} pt ({va_ilum}VA)"
                pot_ilum_total += va_ilum
 
                comp_15 = p + (qtd_lamp * 3.5)
                cabos["1.5mm2"]["Fase"]  += comp_15 * 1.5
                cabos["1.5mm2"]["Neutro"] += comp_15
 
                is_molhada  = any(x in nome for x in ["cozinha", "banheiro", "servico", "lavanderia", "copa", "wc"])
                is_banheiro = any(x in nome for x in ["banheiro", "wc", "suite"])
 
                if is_banheiro:
                    q_tugs, p_tugs = 1, 600
                else:
                    div    = 3.5 if is_molhada else 5.0
                    q_tugs = max(math.ceil(p / div), 1)
                    p_tugs = (min(q_tugs, 3) * 600 + max(0, q_tugs - 3) * 100) if is_molhada else q_tugs * 100
 
                df_calc.at[i, "TUG (Qtd)"]        = int(q_tugs)
                df_calc.at[i, "Potencia TUG (VA)"] = float(p_tugs)
                pot_tug_total += p_tugs
 
                comp_25 = p + (q_tugs * 1.5)
                cabos["2.5mm2"]["Fase"]  += comp_25
                cabos["2.5mm2"]["Neutro"] += comp_25
                cabos["2.5mm2"]["Terra"]  += comp_25
 
                tue_w = float(r["TUE (Watts)"])
                if tue_w > 0:
                    v_tue    = 220 if (tue_w >= 4000 or tensao_fase == 220) else 127
                    corrente = tue_w / v_tue
 
                    if corrente <= 21:   bitola = "2.5mm2"
                    elif corrente <= 28: bitola = "4.0mm2"
                    elif corrente <= 36: bitola = "6.0mm2"
                    else:                bitola = "10.0mm2"
 
                    disjuntor = "20A" if corrente <= 16 else ("25A" if corrente <= 21 else ("32A" if corrente <= 28 else "40A"))
                    tipo_disj = "Bipolar" if v_tue == 220 else "Unipolar"
 
                    novos_circuitos.append({
                        "Circ": f"C{len(novos_circuitos)+3:02d}",
                        "Descricao": f"TUE - {r['Comodo']}",
                        "Potencia": f"{tue_w:.0f}W",
                        "Tensao": f"{v_tue}V",
                        "Cabo": bitola,
                        "Disjuntor": disjuntor,
                        "Tipo Disj.": tipo_disj
                    })
 
                    comp_tue = (p / 2) + 4.0
                    if v_tue == 220 and tensao_fase == 127:
                        cabos[bitola]["Fase"]  += comp_tue * 2
                        cabos[bitola]["Terra"] += comp_tue
                    else:
                        cabos[bitola]["Fase"]  += comp_tue
                        cabos[bitola]["Neutro"] += comp_tue
                        cabos[bitola]["Terra"]  += comp_tue
 
            except Exception as e:
                st.warning(f"Erro na linha {i}: {e}")
                continue
 
        if pot_ilum_total > 0:
            novos_circuitos.insert(0, {"Circ": "C01", "Descricao": "Iluminacao Geral",
                "Potencia": f"{pot_ilum_total}VA", "Tensao": f"{tensao_fase}V",
                "Cabo": "1.5mm2", "Disjuntor": "10A", "Tipo Disj.": "Unipolar"})
        if pot_tug_total > 0:
            novos_circuitos.insert(1, {"Circ": "C02", "Descricao": "Tomadas Gerais (TUGs)",
                "Potencia": f"{pot_tug_total}VA", "Tensao": f"{tensao_fase}V",
                "Cabo": "2.5mm2", "Disjuntor": "20A", "Tipo Disj.": "Unipolar"})
 
        materiais_dinamicos = []
        for bitola, vias in cabos.items():
            if vias["Fase"]  > 0: materiais_dinamicos.append({"Item": f"Cabo Flexivel {bitola} (Fase/Retorno)",  "Qtd": f"{math.ceil(vias['Fase'])}m"})
            if vias["Neutro"] > 0: materiais_dinamicos.append({"Item": f"Cabo Flexivel {bitola} (Neutro - Azul)", "Qtd": f"{math.ceil(vias['Neutro'])}m"})
            if vias.get("Terra", 0) > 0: materiais_dinamicos.append({"Item": f"Cabo Flexivel {bitola} (Terra - Verde)", "Qtd": f"{math.ceil(vias['Terra'])}m"})
 
        contagem_disj = {}
        for c in novos_circuitos:
            dj   = c.get("Disjuntor")
            tipo = c.get("Tipo Disj.", "Unipolar")
            if dj:
                nome_dj = f"Disjuntor DIN {tipo} {dj}"
                contagem_disj[nome_dj] = contagem_disj.get(nome_dj, 0) + 1
        for nome_dj, qtd in contagem_disj.items():
            materiais_dinamicos.append({"Item": nome_dj, "Qtd": f"{qtd} un"})
 
        total_circ = len(novos_circuitos)
        tam_qdc    = 12 if total_circ <= 6 else (16 if total_circ <= 12 else 24)
        materiais_dinamicos.append({"Item": f"Quadro de Distribuicao (QDC) - {tam_qdc} Polos", "Qtd": "1 un"})
 
        st.session_state.dados_cargas     = df_calc
        st.session_state.lista_circuitos  = novos_circuitos
        st.session_state.resumo_materiais = materiais_dinamicos
        st.success("✅ Cálculos e materiais gerados com sucesso!")
        st.rerun()
 
    if st.session_state.lista_circuitos:
        st.divider()
        st.subheader("⚡ Quadro de Circuitos Sugerido (QDC)")
        st.table(pd.DataFrame(st.session_state.lista_circuitos))
        st.subheader("📦 Lista Estimada de Materiais")
        st.table(pd.DataFrame(st.session_state.resumo_materiais))
        st.info("💡 Dica: Verifique sempre a bitola do cabo no 'Dimensionador' antes de fechar o pedido.")
 
        if st.button("📄 Gerar Memorial Técnico Completo (PDF)", use_container_width=True):
            try:
                pdf = FPDF()
                pdf.add_page()
 
                # CABEÇALHO COM DADOS DO PERFIL
                montar_cabecalho_pdf(pdf)
 
                pdf.set_font("Arial", "I", 8)
                pdf.cell(0, 6, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Rede: {tensao_fase}V", 0, 1, "R")
                pdf.ln(3)
 
                # Seção 1: Cargas
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "1. MEMORIAL DE DIMENSIONAMENTO DE CARGAS", "B", 1, "L")
                pdf.ln(3)
                pdf.set_font("Arial", "B", 8)
                pdf.set_fill_color(240, 240, 240)
                h_c = ["Comodo", "Area", "Iluminacao", "TUGs", "Pot.TUG", "TUE"]
                w_c = [45, 20, 35, 20, 35, 35]
                for h, w in zip(h_c, w_c):
                    pdf.cell(w, 8, h, 1, 0, "C", True)
                pdf.ln()
                pdf.set_font("Arial", "", 8)
                for _, r in st.session_state.dados_cargas.iterrows():
                    pdf.cell(45, 7, limpar_texto(str(r["Comodo"])), 1)
                    pdf.cell(20, 7, f"{r['Area (m2)']}m2", 1, 0, "C")
                    pdf.cell(35, 7, limpar_texto(str(r["Iluminacao (VA)"])), 1, 0, "C")
                    pdf.cell(20, 7, str(r["TUG (Qtd)"]), 1, 0, "C")
                    pdf.cell(35, 7, f"{r['Potencia TUG (VA)']}VA", 1, 0, "C")
                    pdf.cell(35, 7, f"{r['TUE (Watts)']}W", 1, 1, "C")
 
                # Seção 2: QDC
                pdf.ln(8)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "2. QUADRO DE DISTRIBUICAO (QDC)", "B", 1, "L")
                pdf.ln(3)
                pdf.set_font("Arial", "B", 8)
                pdf.set_fill_color(240, 240, 240)
                h_q = ["Circ.", "Descricao", "Potencia", "Tensao", "Cabo", "Disj.", "Tipo"]
                w_q = [15, 55, 25, 20, 25, 20, 30]
                for h, w in zip(h_q, w_q):
                    pdf.cell(w, 8, h, 1, 0, "C", True)
                pdf.ln()
                pdf.set_font("Arial", "", 8)
                for c in st.session_state.lista_circuitos:
                    pdf.cell(15, 7, limpar_texto(c["Circ"]), 1, 0, "C")
                    pdf.cell(55, 7, limpar_texto(c["Descricao"]), 1)
                    pdf.cell(25, 7, limpar_texto(c["Potencia"]), 1, 0, "C")
                    pdf.cell(20, 7, limpar_texto(c["Tensao"]), 1, 0, "C")
                    pdf.cell(25, 7, limpar_texto(c["Cabo"]), 1, 0, "C")
                    pdf.cell(20, 7, limpar_texto(c["Disjuntor"]), 1, 0, "C")
                    pdf.cell(30, 7, limpar_texto(c.get("Tipo Disj.", "")), 1, 1, "C")
 
                # Seção 3: Materiais
                pdf.ln(8)
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, "3. MATERIAIS SUGERIDOS (ESTIMATIVA INFRAESTRUTURA)", "B", 1, "L")
                pdf.ln(3)
                pdf.set_font("Arial", "B", 8)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(140, 8, "Item e Especificacao", 1, 0, "C", True)
                pdf.cell(50, 8, "Qtd", 1, 1, "C", True)
                pdf.set_font("Arial", "", 8)
                for m in st.session_state.resumo_materiais:
                    pdf.cell(140, 7, limpar_texto(m["Item"]), 1)
                    pdf.cell(50, 7, limpar_texto(m["Qtd"]), 1, 1, "C")
 
                pdf_out = pdf.output(dest="S").encode("latin-1", "ignore")
                st.download_button("⬇️ Baixar Projeto Completo (PDF)", pdf_out, "Projeto_Eletrico.pdf", "application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"Erro no PDF: {e}")

# --- MÓDULO Luminotecnica  ---
elif aba == "💡 Luminotecnica":
    st.header("💡 Dimensionamento Luminotécnico (NBR ISO/CIE 8995-1)")
    st.info("Este módulo utiliza o Método dos Lúmens para calcular a quantidade de luminárias necessária.")

    # --- 1. ENTRADA DE DADOS DO AMBIENTE ---
    # Note que agora tudo abaixo tem 4 espaços de recuo para estar DENTRO do elif
    with st.expander("🏠 Dados do Ambiente", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            comprimento = st.number_input("Comprimento (m):", min_value=0.1, value=5.0, key="lum_comp")
            largura = st.number_input("Largura (m):", min_value=0.1, value=4.0, key="lum_larg")
        with c2:
            h_total = st.number_input("Pé direito total (m):", min_value=0.1, value=3.0, key="lum_h_total")
            h_trabalho = st.number_input("Altura do plano de trabalho (m):", min_value=0.0, value=0.75, help="Mesa: 0.75m | Chão: 0.0m", key="lum_h_trab")
        with c3:
            h_luminaria = st.number_input("Altura da luminária ao teto (m):", min_value=0.0, value=0.0, help="Embutida: 0.0m", key="lum_h_lum")
        
        # Cálculo da altura útil (h)
        h_util = h_total - h_trabalho - h_luminaria
        area_total = comprimento * largura
        st.write(f"**Área Total:** {area_total:.2f} m² | **Altura Útil (h):** {h_util:.2f} m")

    # --- 2. NORMAS E REFLECTÂNCIA ---
    with st.expander("📚 Parâmetros Normativos"):
        col1, col2 = st.columns(2)
        with col1:
            lux_sugerido = st.selectbox("Tipo de Ambiente (Lux):", [
                "Escritório / Sala de Estudo (500 lux)",
                "Cozinha / Banheiro (300 lux)",
                "Quarto / Sala (150 lux)",
                "Corredor / Depósito (100 lux)",
                "Oficina / Indústria (750 lux)",
                "Personalizado"
            ], key="lum_lux_select")
            
            if lux_sugerido == "Personalizado":
                nivel_iluminancia = st.number_input("Nível de Iluminância desejado (Lux):", value=500, key="lum_lux_custom")
            else:
                nivel_iluminancia = int(lux_sugerido.split('(')[1].split(' ')[0])

        with col2:
            fator_utilizacao = st.slider("Fator de Utilização (η):", 0.1, 1.0, 0.5, help="Depende da luminária e cores das paredes.", key="lum_fu")
            fator_perdas = st.select_slider("Fator de Manutenção (Limpeza):", options=[0.6, 0.7, 0.8], value=0.8, help="0.8: Limpo | 0.7: Médio | 0.6: Sujo", key="lum_fm")

    # --- 3. DADOS DA LUMINÁRIA ---
    with st.expander("🔦 Especificações da Lâmpada/Luminária"):
        c1, c2 = st.columns(2)
        with c1:
            fluxo_unitario = st.number_input("Fluxo Luminoso por Luminária (Lúmens):", min_value=1, value=2500, help="Ver no catálogo do fabricante", key="lum_fluxo_u")
        with c2:
            potencia_unit = st.number_input("Potência por Luminária (W):", min_value=1, value=24, key="lum_pot_u")

    # --- 4. CÁLCULOS FINAIS ---
    fluxo_total_necessario = (nivel_iluminancia * area_total) / (fator_utilizacao * fator_perdas)
    quantidade_n = fluxo_total_necessario / fluxo_unitario
    quantidade_final = int(-(-quantidade_n // 1))  # Arredonda para cima
    
    potencia_total = quantidade_final * potencia_unit
    densidade_potencia = potencia_total / area_total

    # --- 5. RESULTADOS ---
    st.subheader("📊 Resultado do Dimensionamento")
    res1, res2, res3 = st.columns(3)
    res1.metric("Qtd. de Luminárias", f"{quantidade_final} un")
    res2.metric("Potência Total", f"{potencia_total} W")
    res3.metric("W/m²", f"{densidade_potencia:.2f}")

    # Layout Sugerido (Distribuição)
    st.write("---")
    st.subheader("📐 Sugestão de Distribuição")
    import math
    proporcao = comprimento / largura
    colunas = math.sqrt(quantidade_final * proporcao)
    linhas = quantidade_final / colunas
    
    st.write(f"Para uma distribuição uniforme, tente instalar em uma malha de aproximadamente:")
    st.info(f"**{round(colunas)} luminárias ao longo do comprimento** x **{round(linhas)} luminárias ao longo da largura**.")

   # Criamos os dados para passar para o PDF
    dados_atuais = {
        "nivel_lux": nivel_iluminancia,
        "qtd_luminarias": quantidade_final,
        "potencia_total": potencia_total,
        "area": area_total,
        "distribuicao": f"{round(colunas)}x{round(linhas)}"
    }

    # O botão de download precisa gerar o conteúdo na hora
    try:
        pdf_bytes = "gerar_pdf_resultado_lumino" (dados_atuais, st.session_state.get('perfil', {}))
        
        st.download_button(
            label="📥 Gerar e Baixar Relatório (PDF)",
            data=pdf_bytes,
            file_name=f"Luminotecnico_{st.session_state.perfil.get('nome_empresa', 'VoltSpec')}.pdf",
            mime="application/pdf",
            key="btn_download_lumino"
        )
    except Exception as e:
        st.error(f"Erro ao preparar o PDF: {e}")
# --- MÓDULO ORÇAMENTOS ---
elif aba == "💰 Orçamentos":
    st.header("💰 Orçamentos de Serviços")
    cliente = st.text_input("Nome do Cliente:", "Cliente Araxá")
    servicos = [
        {"Descricao": "Ponto de Tomada / Interruptor", "Qtd": 0, "Preco": 85.0},
        {"Descricao": "Ponto de Iluminacao",            "Qtd": 0, "Preco": 75.0},
        {"Descricao": "Montagem de Quadro (ate 12 disj.)",    "Qtd": 0, "Preco": 450.0},
        {"Descricao": "Montagem de Quadro (acima 12 disj.)",  "Qtd": 0, "Preco": 650.0},
        {"Descricao": "Padrao CEMIG Monofasico",         "Qtd": 0, "Preco": 850.0},
        {"Descricao": "Padrao CEMIG Trifasico",          "Qtd": 0, "Preco": 1350.0},
        {"Descricao": "Instalacao de Chuveiro",          "Qtd": 0, "Preco": 110.0},
        {"Descricao": "Laudo de Conformidade",           "Qtd": 0, "Preco": 350.0}
    ]
    df_serv = st.data_editor(pd.DataFrame(servicos), num_rows="dynamic", use_container_width=True, key="orc_edt")
 
    total_orc = (df_serv["Qtd"] * df_serv["Preco"]).sum()
    st.subheader(f"Total Serviços: R$ {total_orc:,.2f}")
 
    if st.button("📄 Gerar PDF Orçamento"):
        pdf = gerar_pdf_universal(f"ORCAMENTO - {cliente}", df_serv, [100, 20, 35, 35], ["Descricao", "Qtd", "Unit.", "Subtotal"])
        st.download_button("⬇️ Baixar PDF", pdf, "Orcamento.pdf", "application/pdf")
 
# --- MÓDULO MATERIAIS ---
elif aba == "📦 Materiais":
    st.header("📦 Lista de Materiais Elétricos")
    materiais = [
        {"Descricao": "Cabo Flexivel 2,5mm (Rolo 100m)", "Qtd": 0, "Preco": 285.0},
        {"Descricao": "Cabo Flexivel 4,0mm (Rolo 100m)", "Qtd": 0, "Preco": 420.0},
        {"Descricao": "Disjuntor DIN Mono (10A a 32A)",  "Qtd": 0, "Preco": 19.90},
        {"Descricao": "Dispositivo DR Bipolar 40A",       "Qtd": 0, "Preco": 189.0},
        {"Descricao": "Dispositivo DPS 20kA",             "Qtd": 0, "Preco": 58.0},
        {"Descricao": "Caixa de Passagem 4x2",            "Qtd": 0, "Preco": 3.50},
        {"Descricao": "Eletroduto Corrugado 3/4 (50m)",   "Qtd": 0, "Preco": 75.0}
    ]
    df_mat = st.data_editor(pd.DataFrame(materiais), num_rows="dynamic", use_container_width=True, key="mat_edt")
 
    total_mat = (df_mat["Qtd"] * df_mat["Preco"]).sum()
    st.subheader(f"Total Materiais: R$ {total_mat:,.2f}")
    st.info("💡 Dica: Verifique sempre a bitola do cabo no 'Dimensionador' antes de fechar o pedido.")
 
    if st.button("📄 Gerar PDF Materiais"):
        pdf = gerar_pdf_universal("LISTA DE MATERIAIS", df_mat, [100, 20, 35, 35], ["Descricao", "Qtd", "Unit.", "Subtotal"])
        st.download_button("⬇️ Baixar PDF", pdf, "Materiais.pdf", "application/pdf")
 
# --- MÓDULO DIMENSIONADOR ---
elif aba == "📐 Dimensionador":
    st.header("📐 Cálculo Técnico Profissional (NBR 5410)")
 
    col_inp1, col_inp2, col_inp3 = st.columns(3)
    with col_inp1:
        pot       = st.number_input("Potência Total (W):", value=1200.0, step=100.0)
        tipo_carga = st.selectbox("Tipo de Carga:", ["Iluminação", "Tomadas (Geral/TUE)"])
    with col_inp2:
        tensao = st.selectbox("Tensão (V):", [127, 220])
        dist   = st.number_input("Distância do Quadro (m):", value=15.0, step=1.0)
    with col_inp3:
        fator_agrup = st.slider("Fator de Agrupamento:", 0.4, 1.0, 1.0,
                                help="0.70 para 3 circuitos no mesmo conduíte")
 
    ib           = pot / tensao
    ib_corrigida = ib / fator_agrup
    bitola_minima = 1.5 if tipo_carga == "Iluminação" else 2.5
 
    if ib_corrigida <= 15.5:   bitola_sugerida = 1.5
    elif ib_corrigida <= 21:   bitola_sugerida = 2.5
    elif ib_corrigida <= 28:   bitola_sugerida = 4.0
    elif ib_corrigida <= 36:   bitola_sugerida = 6.0
    else:                      bitola_sugerida = 10.0
 
    bitola_final     = max(bitola_sugerida, bitola_minima)
    queda_v          = (2 * dist * ib * 0.0172) / bitola_final
    percentual_queda = (queda_v / tensao) * 100
 
    st.divider()
    c_res1, c_res2, c_res3 = st.columns(3)
    with c_res1:
        st.metric("Corrente de Projeto (Ib)", f"{ib:.2f} A")
        if fator_agrup < 1:
            st.caption(f"Ib Corrigida (Agrup.): {ib_corrigida:.2f} A")
    with c_res2:
        color = "normal" if percentual_queda <= 4.0 else "inverse"
        st.metric("Queda de Tensão", f"{percentual_queda:.2f} %", delta=f"{queda_v:.2f} V", delta_color=color)
    with c_res3:
        st.metric("Bitola Final", f"{bitola_final} mm²")
 
    st.subheader("🛡️ Verificação de Conformidade")
    erros, avisos = [], []
    if bitola_sugerida < bitola_minima:
        avisos.append(f"A norma exige mínimo de {bitola_minima}mm² para {tipo_carga.lower()}.")
    if percentual_queda > 4.0:
        erros.append("Queda de tensão acima de 4% (Limite NBR 5410 para circuitos terminais).")
 
    disjuntor_sugerido = math.ceil(ib / 5) * 5
    if disjuntor_sugerido < 10:
        disjuntor_sugerido = 10
 
    if not erros and not avisos:
        st.success("✅ Circuito em conformidade com a NBR 5410.")
    else:
        for erro in erros:   st.error(f"❌ **CONFORMIDADE:** {erro}")
        for aviso in avisos: st.warning(f"⚠️ **OBSERVAÇÃO:** {aviso}")
 
    with st.expander("📝 Detalhes do Dimensionamento"):
        st.write(f"""
        - **Cabo:** Cobre com isolação em PVC (70°C).
        - **Método de Instalação:** Condutos embutidos em alvenaria (B1).
        - **Resistividade (ρ):** 0.0172 Ω·mm²/m.
        - **Disjuntor Sugerido:** {disjuntor_sugerido}A (Curva B para iluminação, C para motores/TUE).
        """)
 
# --- MÓDULO PRODUTOS ---
elif aba == "🛒 Produtos":
    st.header("🛒 Vitrine de Ferramentas (Mercado Livre)")
    prods = [
        {"nome": "Jogo Chaves Isoladas",                     "img": "https://http2.mlstatic.com/D_NQ_NP_2X_701755-MLB85959666529_062025-F.webp",  "link": "https://meli.la/2xLSiQJ"},
        {"nome": "Alicate Decapador Vonder",                 "img": "https://http2.mlstatic.com/D_NQ_NP_2X_608489-MLA99480826142_112025-F.webp",  "link": "https://meli.la/2L47LTv"},
        {"nome": "Bolsa Ferramentas Reforcada",              "img": "https://http2.mlstatic.com/D_NQ_NP_2X_947240-MLA99992405049_112025-F.webp",  "link": "https://meli.la/1E4on12"},
        {"nome": "Alicate Crimpar Prensa",                   "img": "https://http2.mlstatic.com/D_NQ_NP_2X_928036-MLA99440131490_112025-F.webp",  "link": "https://meli.la/247XSK7"},
        {"nome": "Kit Eletrica Chave Teste + Caneta",        "img": "https://http2.mlstatic.com/D_NQ_NP_2X_925244-MLA102644904043_122025-F.webp", "link": "https://meli.la/214x31Y"},
        {"nome": "Alicate Universal Eletricista 1000V",      "img": "https://http2.mlstatic.com/D_NQ_NP_2X_718013-MLA96100316665_102025-F.webp",  "link": "https://meli.la/14aG1bU"},
        {"nome": "Cinto Pochete Porta Ferramentas",          "img": "https://http2.mlstatic.com/D_NQ_NP_2X_993974-MLA96427705692_102025-F.webp",  "link": "https://meli.la/1RKgafT"},
        {"nome": "Cinturao Eletricista Multifuncional",      "img": "https://http2.mlstatic.com/D_NQ_NP_2X_798036-MLB106606586781_022026-F.webp", "link": "https://meli.la/1JcRtAG"},
    ]
    cols = st.columns(4)
    for i, p in enumerate(prods):
        with cols[i % 4]:
            st.image(p["img"], use_container_width=True)
            st.write(f"**{p['nome']}**")
            st.link_button("🚀 Ver no Mercado Livre", p["link"], use_container_width=True)
 
# --- 8. RODAPÉ ---
st.markdown("---")
c_ft1, c_ft2, c_ft3 = st.columns(3)
with c_ft1:
    st.caption(f"📍 {st.session_state.get('endereco', 'Araxá - MG')}")
with c_ft2:
    st.caption("⚡ Desenvolvido por Spec Pro")
with c_ft3:
    if st.session_state.user:
        st.caption(f"🔑 Logado como: {st.session_state.user.email}")
 
# --- FIM DO CÓDIGO ---