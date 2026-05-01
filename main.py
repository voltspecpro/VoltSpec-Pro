import streamlit as st
import pandas as pd
import math
from datetime import datetime, timedelta
from fpdf import FPDF
from supabase import create_client, Client
import io
import unicodedata

# --- 1. CONFIGURAÇÃO DA PÁGINA (ESTÉTICA CLARA) ---
st.set_page_config(
    page_title="VoltSpec Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilo para manter a interface branca e abas limpas
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { background-color: #ffffff; color: #1e293b; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9;
        border-radius: 5px 5px 0px 0px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] { background-color: #3b82f6 !important; color: white !important; }
    .stButton>button { border-radius: 8px; font-weight: bold; height: 3em; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNÇÕES AUXILIARES (PDF E TRATAMENTO) ---
def limpar_texto(texto):
    if not texto: return ""
    return "".join(ch for ch in unicodedata.normalize('NFKD', str(texto)) 
                   if unicodedata.category(ch) != 'Mn').encode('ascii', 'ignore').decode('ascii')

def montar_cabecalho_pdf(pdf, perfil):
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "VOLTSPEC PRO - MEMORIAL TECNICO", 0, 1, "C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, f"Empresa: {perfil.get('empresa', 'N/A')}", 0, 1, "L")
    pdf.cell(0, 5, f"Responsavel: {perfil.get('nome', 'N/A')} | CRT: {perfil.get('crt', 'N/A')}", 0, 1, "L")
    pdf.line(10, 32, 200, 32)
    pdf.ln(10)

# --- 3. CONEXÃO COM BANCO (SUPABASE) ---
URL_SUPA = st.secrets.get("SUPABASE_URL", "")
KEY_SUPA = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_connection():
    try: return create_client(URL_SUPA, KEY_SUPA)
    except: return None

supabase = init_connection()

def verificar_acesso_assinante(email_usuario):
    try:
        if not supabase: return False, "Erro de conexão."
        res = supabase.table("assinaturas").select("*").eq("email", email_usuario.lower().strip()).execute()
        if not res.data: return False, "E-mail não autorizado."
        if res.data[0].get("status") != "ativo": return False, "Acesso pendente."
        return True, "Liberado"
    except: return False, "Erro na verificação."

# --- 4. LOGIN E SEGURANÇA ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.title("⚡ VoltSpec Pro")
        t_auth = st.tabs(["Entrar", "Criar Conta"])
        with t_auth[0]:
            em = st.text_input("E-mail")
            pw = st.text_input("Senha", type="password")
            if st.button("Acessar Sistema"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": em, "password": pw})
                    if res.user:
                        st.session_state.user = res.user
                        st.session_state.logado = True
                        st.rerun()
                except: st.error("Erro no login.")
        with t_auth[1]:
            nem = st.text_input("Novo E-mail")
            npw = st.text_input("Nova Senha", type="password")
            if st.button("Registar"):
                try:
                    supabase.auth.sign_up({"email": nem, "password": npw})
                    st.success("Verifique o seu e-mail!")
                except: st.error("Erro ao criar conta.")
    st.stop()

# Bloqueio de Assinatura
permitido, msg = verificar_acesso_assinante(st.session_state.user.email)
if not permitido:
    st.warning(f"🔒 {msg}")
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()
    st.stop()

# --- 5. INICIALIZAÇÃO DE VARIÁVEIS ---
if 'perfil' not in st.session_state:
    st.session_state.perfil = {'nome': '', 'crt': '', 'empresa': '', 'cnpj': ''}

if 'dados_cargas' not in st.session_state:
    st.session_state.dados_cargas = pd.DataFrame({
        "Comodo": ["Sala", "Cozinha", "Banheiro"],
        "Area (m2)": [15.0, 10.0, 4.5],
        "Perimetro (m)": [16.0, 13.0, 9.0],
        "Iluminacao (VA)": ["-", "-", "-"],
        "TUG (Qtd)": [0, 0, 0],
        "Potencia TUG (VA)": [0.0, 0.0, 0.0],
        "TUE (Watts)": [0.0, 0.0, 5500.0]
    })

if 'lista_circuitos' not in st.session_state: st.session_state.lista_circuitos = []
if 'resumo_materiais' not in st.session_state: st.session_state.resumo_materiais = []

# --- 6. ESTRUTURA DE ABAS INDEPENDENTES ---
st.sidebar.title("VoltSpec Pro ⚡")
if st.sidebar.button("Terminar Sessão"):
    st.session_state.logado = False
    st.rerun()
# --- SE O USUÁRIO TEM ACESSO, MOSTRA O SISTEMA NORMAL ---
aba = st.radio("Navegação:", ["⚙️ Perfil", "🏠 Cargas", "💡 Luminotecnica","❄️ Climatização","☀️ Energia Solar", "📉 Economia", "⚡ Queda de Tensão", "📐 Dimensionador", "💰 Orçamentos", "📦 Materiais", "🛒 Produtos"], horizontal=True)

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
        "salvar_perfil_supabase"

# --- MÓDULO CARGAS ---
elif aba == "🏠 Cargas":
    st.header("📋 Dimensionamento Profissional (NBR 5410 + Materiais)")
 
    with st.expander("🔌 Configuração da Rede e Concessionária", expanded=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            concessionaria = st.selectbox("Selecione a Concessionária:",
                                         ["CEMIG (MG)", "CPFL (SP)", "ENEL (RJ/SP)", "EQUATORIAL", "Outra (Manual)"])
        with col_c2:
            sistema_eletrico = st.selectbox(
                "Sistema Elétrico:",
                ["Monofásico 127V", "Bifásico 220V"],
                index=0
            )
            # Define a tensão base de acordo com o sistema selecionado
            if sistema_eletrico == "Monofásico 127V":
                tensao_fase = 127
                tensao_fase_neutro = 127
            else:  # Bifásico 220V
                tensao_fase = 220
                tensao_fase_neutro = 220
 
    # Inicialização segura do DataFrame
    if 'dados_cargas' not in st.session_state or st.session_state.dados_cargas.columns.tolist() != ["Comodo", "Area (m2)", "Perimetro (m)", "Iluminacao (VA)", "TUG (Qtd)", "Potencia TUG (VA)", "TUE (Watts)"]:
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
        st.session_state.dados_cargas = df_editor.copy()
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
                a = float(r["Area (m2)"] or 0)
                p = float(r["Perimetro (m)"] or 0)
                if a <= 0 or p <= 0: continue
                
                nome = str(r["Comodo"]).lower()
 
                # ===== CÁLCULO ILUMINAÇÃO (NBR 5410) =====
                # Para iluminação geral: 100VA para área ≤ 6m² e +60VA a cada 4m² completos acima disso
                if a <= 6:
                    va_ilum = 100
                else:
                    va_ilum = 100 + (math.floor((a - 6) / 4) * 60)
                
                qtd_lamp = max(math.ceil(va_ilum / 100), 1)
                df_calc.at[i, "Iluminacao (VA)"] = f"{qtd_lamp} pt ({va_ilum}VA)"
                pot_ilum_total += va_ilum
 
                # MATERIAIS ILUMINAÇÃO (Estimativa de metragem - circuito 1.5mm2)
                comp_15 = p + (qtd_lamp * 3.5)
                cabos["1.5mm2"]["Fase"] += comp_15 * 1.5
                cabos["1.5mm2"]["Neutro"] += comp_15
                cabos["1.5mm2"]["Terra"] += comp_15
 
                # ===== CÁLCULO TUGS (NBR 5410) =====
                # Áreas molhadas: mínimo 1 TUG a cada 3,5m de perímetro
                # Áreas secas: mínimo 1 TUG a cada 5,0m de perímetro
                # Banheiros: mínimo 1 TUG a 600VA
                is_molhada = any(x in nome for x in ["cozinha", "banheiro", "servico", "lavanderia", "copa", "wc"])
                is_banheiro = any(x in nome for x in ["banheiro", "wc", "suite"])
 
                if is_banheiro:
                    # Banheiro: mínimo 1 TUG com potência de 600VA
                    q_tugs = 1
                    p_tugs = 600
                else:
                    # Cálculo pela NBR 5410
                    div = 3.5 if is_molhada else 5.0
                    q_tugs = max(math.ceil(p / div), 1)
                    
                    # Potência: primeiras 3 TUGs = 600VA cada; acima = 100VA cada
                    if is_molhada:
                        p_tugs = (min(q_tugs, 3) * 600 + max(0, q_tugs - 3) * 100)
                    else:
                        p_tugs = q_tugs * 100
 
                df_calc.at[i, "TUG (Qtd)"] = int(q_tugs)
                df_calc.at[i, "Potencia TUG (VA)"] = float(p_tugs)
                pot_tug_total += p_tugs
 
                # MATERIAIS TUGS (circuito 2.5mm2)
                comp_25 = p + (q_tugs * 1.5)
                cabos["2.5mm2"]["Fase"] += comp_25
                cabos["2.5mm2"]["Neutro"] += comp_25
                cabos["2.5mm2"]["Terra"] += comp_25
 
                # ===== CÁLCULO TUE (Tomadas de Uso Específico) =====
                tue_w = float(r["TUE (Watts)"] or 0)
                if tue_w > 0:
                    # Define a tensão da TUE de acordo com o sistema selecionado
                    if sistema_eletrico == "Monofásico 127V":
                        v_tue = 127
                    else:  # Bifásico 220V
                        v_tue = 220
                    
                    corrente = tue_w / v_tue
                    
                    # Dimensionamento de bitola conforme corrente (Tabela NBR 5410)
                    if corrente <= 16:
                        bitola = "1.5mm2"
                    elif corrente <= 21:
                        bitola = "2.5mm2"
                    elif corrente <= 28:
                        bitola = "4.0mm2"
                    elif corrente <= 36:
                        bitola = "6.0mm2"
                    else:
                        bitola = "10.0mm2"
 
                    # Dimensionamento do disjuntor
                    if corrente <= 13:
                        disjuntor = "16A"
                    elif corrente <= 16:
                        disjuntor = "20A"
                    elif corrente <= 21:
                        disjuntor = "25A"
                    elif corrente <= 28:
                        disjuntor = "32A"
                    else:
                        disjuntor = "40A"
 
                    # Tipo de disjuntor de acordo com a tensão
                    tipo_disj = "Bipolar" if v_tue == 220 else "Unipolar"
 
                    novos_circuitos.append({
                        "Circ": f"C{len(novos_circuitos)+3:02d}",
                        "Descricao": f"TUE - {r['Comodo']}",
                        "Potencia": f"{tue_w:.0f}W",
                        "Tensao": f"{v_tue}V",
                        "Corrente": f"{corrente:.2f}A",
                        "Cabo": bitola,
                        "Disjuntor": disjuntor,
                        "Tipo Disj.": tipo_disj
                    })
                    
                    # Cálculo de metragem de cabo para TUE
                    comp_tue = (p / 2) + 4.0
                    
                    # Para monofásico 127V: fase + neutro + terra
                    # Para bifásico 220V: 2 fases + terra (sem neutro geralmente)
                    if v_tue == 220 and sistema_eletrico == "Bifásico 220V":
                        cabos[bitola]["Fase"] += comp_tue * 2  # 2 fases
                        cabos[bitola]["Neutro"] += 0  # Sem neutro
                        cabos[bitola]["Terra"] += comp_tue
                    else:
                        cabos[bitola]["Fase"] += comp_tue
                        cabos[bitola]["Neutro"] += comp_tue
                        cabos[bitola]["Terra"] += comp_tue
 
            except Exception as e:
                continue
 
        # ===== ADIÇÃO DE CIRCUITOS GERAIS =====
        if pot_ilum_total > 0:
            novos_circuitos.insert(0, {
                "Circ": "C01",
                "Descricao": "Iluminacao Geral",
                "Potencia": f"{pot_ilum_total}VA",
                "Tensao": f"{tensao_fase}V",
                "Corrente": f"{(pot_ilum_total/tensao_fase):.2f}A",
                "Cabo": "1.5mm2",
                "Disjuntor": "10A",
                "Tipo Disj.": "Unipolar"
            })
        
        if pot_tug_total > 0:
            novos_circuitos.insert(1, {
                "Circ": "C02",
                "Descricao": "Tomadas Gerais (TUGs)",
                "Potencia": f"{pot_tug_total}VA",
                "Tensao": f"{tensao_fase}V",
                "Corrente": f"{(pot_tug_total/tensao_fase):.2f}A",
                "Cabo": "2.5mm2",
                "Disjuntor": "20A",
                "Tipo Disj.": "Unipolar"
            })
 
        # ===== CONSOLIDAÇÃO DE MATERIAIS =====
        materiais_dinamicos = []
        for bitola, vias in cabos.items():
            if vias["Fase"] > 0:
                materiais_dinamicos.append({
                    "Item": f"Cabo Flexivel {bitola} (Fase)",
                    "Qtd": f"{math.ceil(vias['Fase'])}m"
                })
            if vias["Neutro"] > 0:
                materiais_dinamicos.append({
                    "Item": f"Cabo Flexivel {bitola} (Neutro)",
                    "Qtd": f"{math.ceil(vias['Neutro'])}m"
                })
            if vias["Terra"] > 0:
                materiais_dinamicos.append({
                    "Item": f"Cabo Flexivel {bitola} (Terra)",
                    "Qtd": f"{math.ceil(vias['Terra'])}m"
                })
 
        st.session_state.lista_circuitos = novos_circuitos
        st.session_state.resumo_materiais = materiais_dinamicos
        st.session_state.sistema_eletrico = sistema_eletrico
        st.session_state.concessionaria = concessionaria
        st.success("✅ Cálculos realizados com sucesso conforme NBR 5410!")
        st.rerun()
 
    # ===== EXIBIÇÃO DOS RESULTADOS =====
    if st.session_state.get('lista_circuitos'):
        st.divider()
        st.subheader("⚡ Quadro de Circuitos Sugerido (QDC)")
        df_circuitos = pd.DataFrame(st.session_state.lista_circuitos)
        st.dataframe(df_circuitos, use_container_width=True)
        
        st.subheader("📦 Lista Estimada de Materiais")
        df_materiais = pd.DataFrame(st.session_state.resumo_materiais)
        st.dataframe(df_materiais, use_container_width=True)
 
        if st.button("📄 Gerar Memorial Técnico Completo (PDF)", use_container_width=True):
            try:
                from fpdf import FPDF
                from datetime import datetime, timedelta
                
                hoje = datetime.now()
                validade = hoje + timedelta(days=7)
                
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 15, "MEMORIAL TECNICO - PROJETO ELETRICO", 0, 1, "C")
                
                # Informações gerais
                pdf.set_font("Arial", "I", 8)
                pdf.cell(0, 6, f"Gerado em: {hoje.strftime('%d/%m/%Y %H:%M')} | Valido ate: {validade.strftime('%d/%m/%Y')}", 0, 1, "R")
                
                # Configuração da instalação
                pdf.ln(5)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "CONFIGURACAO DA INSTALACAO", 0, 1)
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 6, f"Concessionaria: {st.session_state.get('concessionaria', 'N/A')}", 0, 1)
                pdf.cell(0, 6, f"Sistema Eletrico: {st.session_state.get('sistema_eletrico', 'N/A')}", 0, 1)
                pdf.cell(0, 6, f"Norma Utilizada: NBR 5410 (Instalacoes Eletricas de Baixa Tensao)", 0, 1)
                
                # Tabela de Cargas no PDF
                pdf.ln(5)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "1. MEMORIAL DE CARGAS", 0, 1)
                pdf.ln(2)
                
                pdf.set_font("Arial", "B", 9)
                pdf.set_fill_color(200, 200, 200)
                
                col_widths = [35, 20, 20, 20, 20, 20, 25]
                headers = ["Comodo", "Area", "Ilum.", "TUGs", "Pot.TUG", "TUE", "Perim."]
                
                for header, width in zip(headers, col_widths):
                    pdf.cell(width, 8, header, 1, 0, "C", True)
                pdf.ln()
                
                pdf.set_font("Arial", "", 8)
                pdf.set_fill_color(255, 255, 255)
                
                for _, r in st.session_state.dados_cargas.iterrows():
                    pdf.cell(35, 7, str(r["Comodo"])[:15], 1)
                    pdf.cell(20, 7, f"{float(r['Area (m2)']):.1f}m2", 1, 0, "C")
                    pdf.cell(20, 7, str(r["Iluminacao (VA)"])[:12], 1, 0, "C")
                    pdf.cell(20, 7, str(int(r["TUG (Qtd)"])), 1, 0, "C")
                    pdf.cell(20, 7, f"{float(r['Potencia TUG (VA)']):.0f}VA", 1, 0, "C")
                    pdf.cell(20, 7, f"{float(r['TUE (Watts)']):.0f}W", 1, 0, "C")
                    pdf.cell(25, 7, f"{float(r['Perimetro (m)']):.1f}m", 1, 1, "C")
                
                # Tabela de Circuitos
                pdf.ln(5)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "2. QUADRO DE CIRCUITOS (QDC)", 0, 1)
                pdf.ln(2)
                
                pdf.set_font("Arial", "B", 8)
                pdf.set_fill_color(200, 200, 200)
                
                circ_widths = [15, 30, 20, 15, 18, 15, 18, 15]
                circ_headers = ["Circ", "Descricao", "Potencia", "Tensao", "Corrente", "Cabo", "Disj.", "Tipo"]
                
                for header, width in zip(circ_headers, circ_widths):
                    pdf.cell(width, 8, header, 1, 0, "C", True)
                pdf.ln()
                
                pdf.set_font("Arial", "", 7)
                pdf.set_fill_color(255, 255, 255)
                
                for circ in st.session_state.lista_circuitos:
                    pdf.cell(15, 7, str(circ.get("Circ", "")), 1)
                    pdf.cell(30, 7, str(circ.get("Descricao", ""))[:20], 1, 0, "L")
                    pdf.cell(20, 7, str(circ.get("Potencia", "")), 1, 0, "C")
                    pdf.cell(15, 7, str(circ.get("Tensao", "")), 1, 0, "C")
                    pdf.cell(18, 7, str(circ.get("Corrente", ""))[:10], 1, 0, "C")
                    pdf.cell(15, 7, str(circ.get("Cabo", "")), 1, 0, "C")
                    pdf.cell(18, 7, str(circ.get("Disjuntor", "")), 1, 0, "C")
                    pdf.cell(15, 7, str(circ.get("Tipo Disj.", ""))[:10], 1, 1, "C")
                
                # Tabela de Materiais
                pdf.ln(5)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, "3. LISTA DE MATERIAIS", 0, 1)
                pdf.ln(2)
                
                pdf.set_font("Arial", "B", 9)
                pdf.set_fill_color(200, 200, 200)
                pdf.cell(120, 8, "Material", 1, 0, "L", True)
                pdf.cell(70, 8, "Quantidade", 1, 1, "C", True)
                
                pdf.set_font("Arial", "", 8)
                pdf.set_fill_color(255, 255, 255)
                
                for mat in st.session_state.resumo_materiais:
                    pdf.cell(120, 7, str(mat.get("Item", "")), 1)
                    pdf.cell(70, 7, str(mat.get("Qtd", "")), 1, 1, "C")
                
                # Notas técnicas
                pdf.ln(8)
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 8, "NOTAS TECNICAS:", 0, 1)
                pdf.set_font("Arial", "", 8)
                notas = [
                    "- Todos os calculos foram realizados conforme NBR 5410:2008",
                    "- As bitolas de cabo foram selecionadas com seguranca",
                    "- Os disjuntores sao de curva C (uso residencial/comercial)",
                    "- Considerar topico 6.4.3 da NBR 5410 para agrupamento de circuitos",
                    "- O projeto deve ser executado por eletricista registrado no CREA"
                ]
                for nota in notas:
                    pdf.multi_cell(0, 5, nota)
                
                # Gerar PDF
                pdf_out = pdf.output(dest="S").encode("latin-1", "ignore")
                st.download_button(
                    "⬇️ Baixar Memorial Técnico (PDF)",
                    pdf_out,
                    "Memorial_Tecnico_VoltSpec.pdf",
                    "application/pdf",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"Erro ao gerar PDF: {str(e)}")
# --- MÓDULO Luminotecnica  ---
elif aba == "💡 Luminotecnica":
    st.header("💡 Dimensionamento Luminotécnico (NBR ISO/CIE 8995-1)")
    st.info("Este módulo utiliza o Método dos Lúmens para calcular a quantidade de luminárias necessária.")

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
        
        h_util = h_total - h_trabalho - h_luminaria
        area_total = comprimento * largura
        st.write(f"**Área Total:** {area_total:.2f} m² | **Altura Útil (h):** {h_util:.2f} m")

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

    with st.expander("🔦 Especificações da Lâmpada/Luminária"):
        c1, c2 = st.columns(2)
        with c1:
            fluxo_unitario = st.number_input("Fluxo Luminoso por Luminária (Lúmens):", min_value=1, value=2500, help="Ver no catálogo do fabricante", key="lum_fluxo_u")
        with c2:
            potencia_unit = st.number_input("Potência por Luminária (W):", min_value=1, value=24, key="lum_pot_u")

    fluxo_total_necessario = (nivel_iluminancia * area_total) / (fator_utilizacao * fator_perdas)
    quantidade_n = fluxo_total_necessario / fluxo_unitario
    quantidade_final = int(-(-quantidade_n // 1))
    
    potencia_total = quantidade_final * potencia_unit
    densidade_potencia = potencia_total / area_total if area_total > 0 else 0

    st.subheader("📊 Resultado do Dimensionamento")
    res1, res2, res3 = st.columns(3)
    res1.metric("Qtd. de Luminárias", f"{quantidade_final} un")
    res2.metric("Potência Total", f"{potencia_total} W")
    res3.metric("W/m²", f"{densidade_potencia:.2f}")

    st.write("---")
    st.subheader("📐 Sugestão de Distribuição")
    proporcao = comprimento / largura
    colunas = math.sqrt(quantidade_final * proporcao)
    linhas = quantidade_final / colunas if colunas > 0 else 1
    
    st.write(f"Para uma distribuição uniforme, tente instalar em uma malha de aproximadamente:")
    st.info(f"**{round(colunas)} luminárias ao longo do comprimento** x **{round(linhas)} luminárias ao longo da largura**.")

    dados_atuais = {
        "nivel_lux": nivel_iluminancia,
        "qtd_luminarias": quantidade_final,
        "potencia_total": potencia_total,
        "area": area_total,
        "distribuicao": f"{round(colunas)}x{round(linhas)}"
    }

    try:
        pdf_bytes = "gerar_pdf_resultado_lumino"(dados_atuais, st.session_state.get('perfil', {}))
        if pdf_bytes:
            st.download_button(
                label="📥 Gerar e Baixar Relatório (PDF)",
                data=pdf_bytes,
                file_name=f"Luminotecnico_{st.session_state.perfil.get('nome_empresa', 'VoltSpec')}.pdf",
                mime="application/pdf",
                key="btn_download_lumino"
            )
    except Exception as e:
        st.error(f"Erro ao preparar o PDF: {e}")
# --- MÓDULO CLIMATIZAÇÃO ATUALIZADO ---
elif aba == "❄️ Climatização":
    st.header("❄️ Dimensionamento e Sugestão de Aparelhos")
    st.info("Cálculo de carga térmica e curadoria dos melhores modelos do mercado.")

    # Dicionário de Referência de Modelos (Padrão Inverter de Alta Eficiência)
    modelos_referencia = {
        7000:  "LG Dual Inverter Voice ou Samsung WindFree",
        9000:  "LG Dual Inverter Voice / Samsung WindFree / Daikin EcoSwing",
        12000: "LG Dual Inverter Voice / Samsung WindFree / Gree G-Top",
        18000: "LG Dual Inverter Voice / Daikin EcoSwing / Midea Xtreme Save",
        24000: "LG Dual Inverter Voice / Gree G-Top Inverter",
        30000: "Gree G-Top Inverter / LG Dual Inverter (Artcool)",
        36000: "Carrier XPower Inverter / Elgin Eco Power",
        48000: "Trane Inverter / Carrier Piso Teto",
        60000: "Carrier / York (Piso Teto ou Cassete)"
    }

    with st.expander("🏠 Características do Ambiente", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            area_clima = st.number_input("Área do Ambiente (m²):", min_value=1.0, value=15.0)
            exposicao_sol = st.selectbox("Exposição ao Sol:", ["Manhã ou Sombra (600 BTUs/m²)", "Tarde ou Sol Forte (800 BTUs/m²)"])
        with c2:
            num_pessoas = st.number_input("Número de Pessoas (além de você):", min_value=0, value=1)
            num_eletronicos = st.number_input("Número de Eletrônicos (TV, PC, etc):", min_value=0, value=1)

    # Lógica do Cálculo
    fator_area = 800 if "Sol Forte" in exposicao_sol else 600
    btu_base = area_clima * fator_area
    btu_pessoas = num_pessoas * 600
    btu_aparelhos = num_eletronicos * 600
    total_btus = btu_base + btu_pessoas + btu_aparelhos

    # Sugestão de Aparelho Comercial
    comerciais = sorted(modelos_referencia.keys())
    sugestao_btu = comerciais[0]
    for c in comerciais:
        if c >= total_btus:
            sugestao_btu = c
            break
    
    modelo_nome = modelos_referencia.get(sugestao_btu, "Consulte um especialista para grandes áreas")

    st.divider()
    res_c1, res_c2 = st.columns(2)
    with res_c1:
        st.metric("Carga Térmica Total", f"{int(total_btus)} BTUs")
    with res_c2:
        st.metric("Capacidade Comercial", f"{sugestao_btu} BTUs", delta="Sugerido")

    st.success(f"🏆 **Modelos Recomendados (Linha Inverter):** \n\n {modelo_nome}")
    st.caption("Priorizamos marcas com maior rede de assistência técnica e eficiência energética (Selo Procel A).")

    # --- GERAÇÃO DE PDF CLIMATIZAÇÃO ATUALIZADO ---
    if st.button("📄 Gerar Relatório com Sugestão de Marcas", use_container_width=True):
        try:
            pdf = "FPDF"()
            pdf.add_page()
            "montar_cabecalho_pdf"(pdf)

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "RELATÓRIO DE DIMENSIONAMENTO E COMPRA", "B", 1, "C")
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "1. Detalhes do Ambiente", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, f"- Área: {area_clima} m2 | Carga Calculada: {int(total_btus)} BTUs", 0, 1)
            pdf.cell(0, 6, f"- Fator Solar: {exposicao_sol}", 0, 1)

            pdf.ln(5)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "2. Recomendação de Equipamento", 0, 1)
            
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, f"Capacidade Necessária: {sugestao_btu} BTUs", 1, 1, "C", True)
            
            pdf.ln(2)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 8, "Marcas e Modelos Sugeridos (Alta Eficiência):", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 8, f"{modelo_nome}", 1, "C")

            pdf.ln(10)
            pdf.set_font("Arial", "I", 9)
            pdf.multi_cell(0, 5, "Nota Técnica: Recomendamos a instalação de modelos com tecnologia INVERTER "
                               "para economia de até 70% na conta de luz. A instalação deve seguir as "
                               "normas do fabricante para preservação da garantia.")

            pdf_output = pdf.output(dest="S").encode("latin-1", "ignore")
            st.download_button("⬇️ Baixar Relatório de Compra", pdf_output, "Guia_Compra_Ar.pdf", "application/pdf", use_container_width=True)
            
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")
# --- MÓDULO ENERGIA SOLAR ---
elif aba == "☀️ Energia Solar":
    st.header("☀️ Estimativa Solar Fotovoltaica")
    st.info("Gere uma estimativa rápida de investimento e economia para sistemas On-Grid.")

    with st.expander("📊 Dados de Consumo e Local", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            consumo_kwh = st.number_input("Consumo Médio Mensal (kWh):", min_value=50.0, value=400.0, step=10.0)
            tarifa_energia = st.number_input("Preço do kWh (com impostos - R$):", min_value=0.1, value=0.95, step=0.01)
        with c2:
            potencia_painel = st.selectbox("Potência do Painel (Watts):", [450, 550, 600, 650], index=1)
            eficiencia_sistema = 0.80 # 20% de perdas

    # Lógica do Cálculo Técnico
    # Fórmula: Potência (kWp) = Consumo / (30 dias * HSP * Eficiência)
    hsp_araxa = 5.2 
    potencia_necessaria_kwp = consumo_kwh / (30 * hsp_araxa * eficiencia_sistema)
    
    # Quantidade de Painéis
    qtd_paineis = math.ceil((potencia_necessaria_kwp * 1000) / potencia_painel)
    potencia_real_instalada = (qtd_paineis * potencia_painel) / 1000
    
    # Estimativa de Área (Média de 2.6m² por painel de 550W)
    area_estimada = qtd_paineis * 2.6

    # Financeiro (Estimativa de mercado: R$ 3,80 por Wp instalado)
    investimento_estimado = potencia_real_instalada * 1000 * 3.80
    economia_mensal = consumo_kwh * tarifa_energia
    payback_meses = investimento_estimado / economia_mensal if economia_mensal > 0 else 0

    # Exibição dos Resultados
    st.divider()
    res1, res2, res3 = st.columns(3)
    res1.metric("Painéis Necessários", f"{qtd_paineis} un")
    res2.metric("Potência do Sistema", f"{potencia_real_instalada:.2f} kWp")
    res3.metric("Área no Telhado", f"{area_estimada:.1f} m²")

    fin1, fin2 = st.columns(2)
    fin1.metric("Investimento Estimado", f"R$ {investimento_estimado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    fin2.metric("Payback (Retorno)", f"{math.ceil(payback_meses/12)} anos", f"{int(payback_meses)} meses")

    # --- GERAÇÃO DE PDF SOLAR ---
    if st.button("📄 Gerar Estudo de Viabilidade Solar (PDF)", use_container_width=True):
        try:
            pdf = "FPDF"()
            pdf.add_page()
            "montar_cabecalho_pdf"(pdf)

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "ESTUDO PRELIMINAR DE VIABILIDADE SOLAR", "B", 1, "C")
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "1. Resumo do Dimensionamento", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, f"- Consumo Mensal Alvo: {consumo_kwh} kWh", 0, 1)
            pdf.cell(0, 7, f"- Potência Geradora Recomendada: {potencia_real_instalada:.2f} kWp", 0, 1)
            pdf.cell(0, 7, f"- Quantidade de Módulos ({potencia_painel}W): {qtd_paineis} unidades", 0, 1)
            pdf.cell(0, 7, f"- Espaço Necessário em Telhado: {area_estimada:.1f} m2", 0, 1)

            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "2. Análise Financeira Estimada", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, f"- Investimento Aproximado: R$ {investimento_estimado:,.2f}", 0, 1)
            pdf.cell(0, 7, f"- Economia Mensal Estimada: R$ {economia_mensal:,.2f}", 0, 1)
            pdf.cell(0, 7, f"- Tempo de Retorno (Payback): aprox. {math.ceil(payback_meses/12)} anos", 0, 1)

            pdf.ln(10)
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Arial", "I", 9)
            pdf.multi_cell(0, 5, "AVISO: Este relatório é uma estimativa baseada na média de radiação solar da região (HSP 5.2). "
                               "Os valores de investimento podem variar conforme a marca dos equipamentos, tipo de telhado e "
                               "distância do quadro de energia. Requer visita técnica e projeto executivo.", 1, "J", True)

            pdf_output = pdf.output(dest="S").encode("latin-1", "ignore")
            st.download_button("⬇️ Baixar Estudo Solar", pdf_output, "Estudo_Solar_VoltSpec.pdf", "application/pdf", use_container_width=True)
            
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")
# --- MÓDULO SIMULADOR DE ECONOMIA ---
elif aba == "📉 Economia":
    st.header("📉 Simulador de Economia de Energia")
    st.info("Mostre ao seu cliente quanto ele economiza ao modernizar as instalações.")

    with st.expander("💡 Modernização de Iluminação", expanded=True):
        col_ilum1, col_ilum2 = st.columns(2)
        with col_ilum1:
            tipo_antiga = st.selectbox("Tipo de Lâmpada Atual:", ["Incandescente (60W)", "Fluorescente (40W)"])
            qtd_lampadas = st.number_input("Quantidade de Lâmpadas:", min_value=1, value=10)
        with col_ilum2:
            horas_uso = st.number_input("Horas de uso por dia:", min_value=1, max_value=24, value=6)
            tarifa_simulada = st.number_input("Tarifa de Energia (R$/kWh):", value=0.95, key="tarifa_eco")

    # Lógica Iluminação
    watts_antiga = 60 if "Incandescente" in tipo_antiga else 40
    watts_nova = 9 if "Incandescente" in tipo_antiga else 18
    
    consumo_mensal_antigo = (watts_antiga * qtd_lampadas * horas_uso * 30) / 1000
    consumo_mensal_novo = (watts_nova * qtd_lampadas * horas_uso * 30) / 1000
    economia_kwh_mes = consumo_mensal_antigo - consumo_mensal_novo
    economia_rs_mes = economia_kwh_mes * tarifa_simulada

    st.divider()
    
    with st.expander("❄️ Upgrade para Ar-Condicionado Inverter"):
        col_ar1, col_ar2 = st.columns(2)
        with col_ar1:
            btu_ar = st.selectbox("Potência do Aparelho (BTUs):", [9000, 12000, 18000, 24000])
            dias_uso_mes = st.slider("Dias de uso no mês:", 1, 30, 22)
        with col_ar2:
            horas_ar = st.slider("Horas por dia:", 1, 24, 8)
    
    # Lógica Ar-Condicionado (Estimativa média de consumo)
    # Convencional consome aprox. 1.1kWh por 9000 BTUs (em regime). Inverter economiza 40%.
    consumo_ref_hora = (btu_ar / 9000) * 1.0 # Base 1kWh para cada 9k BTUs
    consumo_ar_conv = consumo_ref_hora * horas_ar * dias_uso_mes
    economia_ar_rs = (consumo_ar_conv * 0.40) * tarifa_simulada # 40% de economia

    # Resumo Geral
    st.subheader("💰 Potencial de Economia Total")
    total_eco_mes = economia_rs_mes + economia_ar_rs
    total_eco_ano = total_eco_mes * 12

    res_e1, res_e2 = st.columns(2)
    res_e1.metric("Economia Mensal Estimada", f"R$ {total_eco_mes:.2f}")
    res_e2.metric("Economia Anual Estimada", f"R$ {total_eco_ano:.2f}", delta="Redução de Custos")

    # --- GERAÇÃO DE PDF ECONOMIA ---
    if st.button("📄 Gerar Laudo de Economia (PDF)", use_container_width=True):
        try:
            pdf = "FPDF"()
            pdf.add_page()
            "montar_cabecalho_pdf"(pdf)

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "LAUDO TÉCNICO DE POTENCIAL DE ECONOMIA", "B", 1, "C")
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "1. Modernização da Iluminação", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, f"- Troca de {qtd_lampadas} unidades de lâmpadas {tipo_antiga} por LED.", 0, 1)
            pdf.cell(0, 7, f"- Redução mensal de consumo: {economia_kwh_mes:.2f} kWh", 0, 1)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 7, f"- Economia financeira em iluminação: R$ {economia_rs_mes:.2f}/mês", 0, 1)

            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "2. Eficiência em Climatização (Inverter)", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, f"- Upgrade para tecnologia Inverter em aparelho de {btu_ar} BTUs.", 0, 1)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 7, f"- Economia financeira em climatização: R$ {economia_ar_rs:.2f}/mês", 0, 1)

            pdf.ln(10)
            pdf.set_fill_color(0, 128, 0)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 12, f"ECONOMIA TOTAL ESTIMADA: R$ {total_eco_ano:.2f} POR ANO", 0, 1, "C", True)
            
            pdf.set_text_color(0, 0, 0)
            pdf.ln(5)
            pdf.set_font("Arial", "I", 9)
            pdf.multi_cell(0, 5, "Nota: Este simulador utiliza médias de consumo baseadas em especificações técnicas de fabricantes. "
                               "A economia real pode variar de acordo com a marca dos equipamentos e hábitos de uso.")

            pdf_output = pdf.output(dest="S").encode("latin-1", "ignore")
            st.download_button("⬇️ Baixar Laudo de Economia", pdf_output, "Laudo_Economia_VoltSpec.pdf", "application/pdf", use_container_width=True)
            
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

# --- MÓDULO ORÇAMENTOS ---
elif aba == "💰 Orçamentos":
    st.header("💰 Orçamentos de Serviços")
    cliente = st.text_input("Nome do Cliente:", "Cliente Araxá")
    servicos = [
        {"Descricao": "Ponto de Tomada / Interruptor", "Qtd": 0, "Preco": 85.0},
        {"Descricao": "Ponto de Iluminacao",            "Qtd": 0, "Preco": 75.0},
        {"Descricao": "Montagem de Quadro (ate 12 disj.)",    "Qtd": 0, "Preco": 450.0},
        {"Descricao": "Montagem de Quadro (acima 12 disj.)",  "Qtd": 0, "Preco": 650.0},
        {"Descricao": "Padrao CEMIG Monofasico",        "Qtd": 0, "Preco": 850.0},
        {"Descricao": "Padrao CEMIG Trifasico",          "Qtd": 0, "Preco": 1350.0},
        {"Descricao": "Instalacao de Chuveiro",          "Qtd": 0, "Preco": 110.0},
        {"Descricao": "Laudo de Conformidade",           "Qtd": 0, "Preco": 350.0}
    ]
    df_serv = st.data_editor(pd.DataFrame(servicos), num_rows="dynamic", use_container_width=True, key="orc_edt")

    total_orc = (df_serv["Qtd"] * df_serv["Preco"]).sum()
    st.subheader(f"Total Serviços: R$ {total_orc:,.2f}")

    if st.button("📄 Gerar PDF Orçamento"):
        pdf = "gerar_pdf_universal"(f"ORCAMENTO - {cliente}", df_serv, [100, 20, 35, 35], ["Descricao", "Qtd", "Unit.", "Subtotal"])
        if pdf:
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
        pdf = "gerar_pdf_universal"("LISTA DE MATERIAIS", df_mat, [100, 20, 35, 35], ["Descricao", "Qtd", "Unit.", "Subtotal"])
        if pdf:
            st.download_button("⬇️ Baixar PDF", pdf, "Materiais.pdf", "application/pdf")
            # --- MÓDULO QUEDA DE TENSÃO REAL ---
elif aba == "⚡ Queda de Tensão":
    st.header("⚡ Diagnóstico de Queda de Tensão (NBR 5410)")
    st.info("Verifique se a fiação existente está perdendo energia e colocando os equipamentos em risco.")

    with st.expander("🔌 Dados da Instalação", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            v_nominal = st.selectbox("Tensão Nominal (V):", [127, 220, 380, 440])
            corrente_a = st.number_input("Corrente Medida/Carga (A):", min_value=0.1, value=10.0)
            distancia_m = st.number_input("Distância do Cabo (metros):", min_value=1.0, value=20.0)
        with c2:
            secao_cabo = st.selectbox("Seção do Cabo Atual (mm²):", [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50])
            material_cabo = st.radio("Material do Condutor:", ["Cobre", "Alumínio"], horizontal=True)
            fase_sistema = st.radio("Tipo de Circuito:", ["Monofásico/Bifásico", "Trifásico"], horizontal=True)

    # Lógica do Cálculo Técnico (Fórmula: DeltaV = (k * L * I * rho) / S)
    # rho cobre = 0.0172 / rho aluminio = 0.0282
    rho = 0.0172 if material_cabo == "Cobre" else 0.0282
    k = 2 if fase_sistema == "Monofásico/Bifásico" else 1.732 # Fator de distância ida/volta ou trifásico
    
    queda_volts = (k * rho * distancia_m * corrente_a) / secao_cabo
    queda_percentual = (queda_volts / v_nominal) * 100
    v_final = v_nominal - queda_volts

    # Critérios NBR 5410 (Geralmente 4% para circuitos terminais)
    limite_norma = 4.0
    esta_dentro = queda_percentual <= limite_norma

    st.divider()
    res1, res2, res3 = st.columns(3)
    res1.metric("Queda em Volts", f"{queda_volts:.2f} V")
    
    # Cor do indicador de percentual
    if esta_dentro:
        res2.metric("Queda Percentual", f"{queda_percentual:.2f} %", "✅ Dentro da Norma", delta_color="normal")
    else:
        res2.metric("Queda Percentual", f"{queda_percentual:.2f} %", "⚠️ Fora da Norma", delta_color="inverse")
        
    res3.metric("Tensão na Carga", f"{v_final:.1f} V")

    # Alerta Visual
    if not esta_dentro:
        st.warning(f"🚨 **Atenção:** A queda de tensão ultrapassou os {limite_norma}% recomendados pela NBR 5410. "
                   "Isso causa aquecimento dos cabos, desperdício de energia e pode danificar motores e eletrônicos.")
    else:
        st.success("✅ A fiação está adequadamente dimensionada para esta distância e carga.")

    # --- GERAÇÃO DE PDF DIAGNÓSTICO ---
    if st.button("📄 Gerar Laudo de Conformidade Elétrica (PDF)", use_container_width=True):
        try:
            pdf = "FPDF"()
            pdf.add_page()
            "montar_cabecalho_pdf"(pdf)

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "LAUDO TÉCNICO DE QUEDA DE TENSÃO", "B", 1, "C")
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "1. Parâmetros Analisados", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, f"- Tensão de Origem: {v_nominal}V | Circuito: {fase_sistema}", 0, 1)
            pdf.cell(0, 7, f"- Condutor: {secao_cabo}mm2 em {material_cabo}", 0, 1)
            pdf.cell(0, 7, f"- Comprimento do Trecho: {distancia_m} metros", 0, 1)
            pdf.cell(0, 7, f"- Corrente de Projeto: {corrente_a} A", 0, 1)

            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "2. Resultados do Diagnóstico", 0, 1)
            pdf.set_font("Arial", "B", 12)
            
            status_texto = "CONFORME (DENTRO DA NORMA)" if esta_dentro else "NÃO CONFORME (FORA DA NORMA)"
            pdf.cell(0, 10, f"STATUS: {status_texto}", 1, 1, "C")
            
            pdf.set_font("Arial", "", 10)
            pdf.ln(2)
            pdf.cell(0, 7, f"- Queda de Tensão Calculada: {queda_volts:.2f} V", 0, 1)
            pdf.cell(0, 7, f"- Percentual de Perda: {queda_percentual:.2f}% (Limite NBR 5410: {limite_norma}%)", 0, 1)
            pdf.cell(0, 7, f"- Tensão Final Disponível no Equipamento: {v_final:.1f} V", 0, 1)

            if not esta_dentro:
                pdf.ln(5)
                pdf.set_text_color(200, 0, 0)
                pdf.set_font("Arial", "B", 10)
                pdf.multi_cell(0, 6, "RECOMENDAÇÃO TÉCNICA: É necessária a substituição dos condutores por uma seção superior "
                                   "ou a redistribuição das cargas para reduzir a distância do circuito, visando evitar "
                                   "sobreaquecimento e perda de eficiência energética.")
            
            pdf.set_text_color(0, 0, 0)
            pdf_output = pdf.output(dest="S").encode("latin-1", "ignore")
            st.download_button("⬇️ Baixar Laudo de Diagnóstico", pdf_output, "Laudo_Tecnico_Queda_Tensao.pdf", "application/pdf", use_container_width=True)
            
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

# --- MÓDULO DIMENSIONADOR ---
elif aba == "📐 Dimensionador":
    st.header("📐 Cálculo Técnico Profissional (NBR 5410)")

    col_inp1, col_inp2, col_inp3 = st.columns(3)
    with col_inp1:
        pot        = st.number_input("Potência Total (W):", value=1200.0, step=100.0)
        tipo_carga = st.selectbox("Tipo de Carga:", ["Iluminação", "Tomadas (Geral/TUE)"])
    with col_inp2:
        tensao = st.selectbox("Tensão (V):", [127, 220])
        dist   = st.number_input("Distância do Quadro (m):", value=15.0, step=1.0)
    with col_inp3:
        fator_agrup = st.slider("Fator de Agrupamento:", 0.4, 1.0, 1.0, help="0.70 para 3 circuitos no mesmo conduíte")

    ib = pot / tensao
    ib_corrigida = ib / fator_agrup
    bitola_minima = 1.5 if tipo_carga == "Iluminação" else 2.5

    if ib_corrigida <= 15.5:   bitola_sugerida = 1.5
    elif ib_corrigida <= 21:   bitola_sugerida = 2.5
    elif ib_corrigida <= 28:   bitola_sugerida = 4.0
    elif ib_corrigida <= 36:   bitola_sugerida = 6.0
    else:                      bitola_sugerida = 10.0

    bitola_final     = max(bitola_sugerida, bitola_minima)
    queda_v          = (2 * dist * ib * 0.0172) / bitola_final
    percentual_queda = (queda_v / tensao) * 100 if tensao > 0 else 0

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

    # --- INÍCIO DA ADIÇÃO: DIMENSIONAMENTO DE ELETRODUTOS ---
    st.subheader("🕳️ Ocupação do Eletroduto")
    
    # Valores de referência comerciais aproximados (em mm²)
    area_cabos = {1.5: 6.0, 2.5: 7.5, 4.0: 11.0, 6.0: 14.5, 10.0: 22.5}
    area_eletrodutos = {"20mm (1/2\")": 176, "25mm (3/4\")": 283, "32mm (1\")": 530, "40mm (1 1/4\")": 907}

    col_el1, col_el2 = st.columns(2)
    with col_el1:
        qtd_condutores = st.number_input("Qtd. de Condutores no Trecho:", min_value=1, value=3, step=1, help="Ex: Fase + Neutro + Terra")
    with col_el2:
        eletroduto_escolhido = st.selectbox("Tamanho do Eletroduto:", list(area_eletrodutos.keys()))

    # Lógica de cálculo
    area_unitaria_cabo = area_cabos.get(bitola_final, bitola_final * 2.5) # Se a bitola passar de 10mm², usa um fator de segurança
    area_total_cabos = area_unitaria_cabo * qtd_condutores
    area_eletroduto = area_eletrodutos[eletroduto_escolhido]
    
    taxa_ocupacao = (area_total_cabos / area_eletroduto) * 100

    # Definição dos limites da norma
    if qtd_condutores == 1:
        limite_ocupacao = 53
    elif qtd_condutores == 2:
        limite_ocupacao = 31
    else:
        limite_ocupacao = 40

    # Feedback visual com barra de progresso no Streamlit
    cor_barra = "green" if taxa_ocupacao <= limite_ocupacao else "red"
    st.progress(min(taxa_ocupacao / 100, 1.0))
    st.caption(f"Ocupação atual: **{taxa_ocupacao:.1f}%** | Limite NBR 5410: **{limite_ocupacao}%**")
    # --- FIM DA ADIÇÃO ---

    st.subheader("🛡️ Verificação de Conformidade")
    erros, avisos = [], []
    
    if bitola_sugerida < bitola_minima:
        avisos.append(f"A norma exige mínimo de {bitola_minima}mm² para {tipo_carga.lower()}.")
    if percentual_queda > 4.0:
        erros.append("Queda de tensão acima de 4% (Limite NBR 5410 para circuitos terminais).")
        
    # Integração do eletroduto na verificação de erros
    if taxa_ocupacao > limite_ocupacao:
        erros.append(f"Eletroduto superlotado! A taxa de {taxa_ocupacao:.1f}% ultrapassa o limite de {limite_ocupacao}% para {qtd_condutores} condutores.")

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
        - **Eletroduto:** {eletroduto_escolhido} (Área ocupada: {area_total_cabos:.1f} mm² de {area_eletroduto} mm²).
        """)

# --- MÓDULO PRODUTOS ---
elif aba == "🛒 Produtos":
    st.header("🛒 Vitrine de Ferramentas (Mercado Livre)")
    st.markdown("Aproveite as melhores oportunidades e descontos para equipar sua mala de ferramentas.")
    
    prods = [
        {"nome": "Jogo Chaves Isoladas",                     "img": "https://http2.mlstatic.com/D_NQ_NP_2X_701755-MLB85959666529_062025-F.webp",  "link": "https://meli.la/2xLSiQJ"},
        {"nome": "Alicate Decapador Vonder",                 "img": "https://http2.mlstatic.com/D_NQ_NP_2X_608489-MLA99480826142_112025-F.webp",  "link": "https://meli.la/2L47LTv"},
        {"nome": "Bolsa Ferramentas Reforçada",              "img": "https://http2.mlstatic.com/D_NQ_NP_2X_947240-MLA99992405049_112025-F.webp",  "link": "https://meli.la/1E4on12"},
        {"nome": "Alicate Crimpar Prensa",                   "img": "https://http2.mlstatic.com/D_NQ_NP_2X_928036-MLA99440131490_112025-F.webp",  "link": "https://meli.la/247XSK7"},
        {"nome": "Kit Elétrica Chave Teste + Caneta",        "img": "https://http2.mlstatic.com/D_NQ_NP_2X_925244-MLA102644904043_122025-F.webp", "link": "https://meli.la/214x31Y"},
        {"nome": "Alicate Universal Eletricista 1000V",      "img": "https://http2.mlstatic.com/D_NQ_NP_2X_718013-MLA96100316665_102025-F.webp",  "link": "https://meli.la/14aG1bU"},
        {"nome": "Cinto Pochete Porta Ferramentas",          "img": "https://http2.mlstatic.com/D_NQ_NP_2X_993974-MLA96427705692_102025-F.webp",  "link": "https://meli.la/1RKgafT"},
        {"nome": "Cinturão Eletricista Multifuncional",      "img": "https://http2.mlstatic.com/D_NQ_NP_2X_798036-MLB106606586781_022026-F.webp", "link": "https://meli.la/1JcRtAG"},
    ]
    
    cols = st.columns(4)
    for i, p in enumerate(prods):
        with cols[i % 4]:
            # Criamos um "card" com altura fixa e fundo branco usando HTML
            html_img = f"""
            <div style="background-color: white; border-radius: 10px; padding: 10px; display: flex; justify-content: center; align-items: center; height: 160px; margin-bottom: 10px;">
                <img src="{p['img']}" style="max-width: 100%; max-height: 100%; object-fit: contain;">
            </div>
            """
            st.markdown(html_img, unsafe_allow_html=True)
            
            # Travamos também a altura do título para os botões não desalinharem
            st.markdown(f"<div style='height: 45px; text-align: center; font-size: 14px;'><b>{p['nome']}</b></div>", unsafe_allow_html=True)
            
            st.link_button("🚀 Ver Oferta", p["link"], use_container_width=True)

# --- 8. RODAPÉ ---
st.markdown("---")
c_ft1, c_ft2, c_ft3 = st.columns(3)
with c_ft1:
    st.caption(f"📍 {st.session_state.perfil.get('endereco', '')}")
with c_ft2:
    st.caption("⚡ Desenvolvido por Spec Pro")
with c_ft3:
    if st.session_state.get('user'):
        st.caption(f"🔑 Logado como: {st.session_state.user.email}")