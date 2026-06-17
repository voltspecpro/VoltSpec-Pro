import streamlit as st
import pandas as pd
import math
from datetime import datetime, timedelta
from fpdf import FPDF
import io
import unicodedata

# --- 1. CONFIGURAÇÃO DA PÁGINA (ESTÉTICA MOBILE) ---
st.set_page_config(
    page_title="VoltSpec Pocket",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Estilo para manter a interface limpa e os botões bonitos
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { background-color: #ffffff; color: #1e293b; }
    .stButton>button { border-radius: 8px; font-weight: bold; height: 3em; width: 100%; }
    
    /* Estilização para o menu horizontal (radio) ficar parecendo botões de app */
    div.row-widget.stRadio > div { flex-direction: row; flex-wrap: wrap; justify-content: center; gap: 10px; }
    div.row-widget.stRadio > div > label { 
        background-color: #f1f5f9; 
        padding: 10px 15px; 
        border-radius: 8px; 
        cursor: pointer;
    }
    div.row-widget.stRadio > div > label[data-baseweb="radio"]:hover { background-color: #e2e8f0; }
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
    nome_empresa = perfil.get('nome_empresa', 'N/A')
    crt = perfil.get('crt', 'N/A')
    pdf.cell(0, 5, f"Empresa: {nome_empresa}", 0, 1, "L")
    pdf.cell(0, 5, f"Responsavel: {nome_empresa} | CRT: {crt}", 0, 1, "L")
    pdf.line(10, 32, 200, 32)
    pdf.ln(10)

def gerar_pdf_universal(titulo, df_dados, col_widths, headers):
    pdf = FPDF()
    pdf.add_page()
    montar_cabecalho_pdf(pdf, st.session_state.perfil)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, titulo, 0, 1, "C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 200, 200)
    for header, width in zip(headers, col_widths):
        pdf.cell(width, 8, header, 1, 0, "C", True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    total = 0
    for _, row in df_dados.iterrows():
        descricao = str(row.get("Descricao", ""))[:45]
        qtd = float(row.get("Qtd", 0))
        preco = float(row.get("Preco", 0.0))
        
        subtotal = qtd * preco
        total += subtotal
        
        pdf.cell(col_widths[0], 8, descricao, 1)
        pdf.cell(col_widths[1], 8, str(int(qtd)), 1, 0, "C")
        pdf.cell(col_widths[2], 8, f"R$ {preco:.2f}", 1, 0, "C")
        pdf.cell(col_widths[3], 8, f"R$ {subtotal:.2f}", 1, 1, "C")
        
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"TOTAL GERAL: R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), 0, 1, "R")
    
    return pdf.output(dest="S").encode("latin-1", "ignore")

def gerar_pdf_resultado_lumino(dados_atuais, perfil):
    pdf = FPDF()
    pdf.add_page()
    montar_cabecalho_pdf(pdf, perfil)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "PROJETO LUMINOTECNICO (METODO DOS LUMENS)", 0, 1, "C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"- Nivel de Iluminancia Desejado: {dados_atuais['nivel_lux']} Lux", 0, 1)
    pdf.cell(0, 8, f"- Area do Ambiente: {dados_atuais['area']:.2f} m2", 0, 1)
    pdf.cell(0, 8, f"- Quantidade de Luminarias Necessarias: {dados_atuais['qtd_luminarias']} unidades", 0, 1)
    pdf.cell(0, 8, f"- Potencia Total Instalada: {dados_atuais['potencia_total']} W", 0, 1)
    pdf.cell(0, 8, f"- Sugestao de Distribuicao (Comprimento x Largura): {dados_atuais['distribuicao']}", 0, 1)
    
    return pdf.output(dest="S").encode("latin-1", "ignore")

# --- 3. INICIALIZAÇÃO DE VARIÁVEIS ---
if 'perfil' not in st.session_state:
    st.session_state.perfil = {'nome_empresa': '', 'crt': '', 'cnpj': '', 'telefone': '', 'email_contato': '', 'endereco': ''}

# Garantindo a estrutura correta para não sumir as colunas
if 'dados_cargas' not in st.session_state or st.session_state.dados_cargas.columns.tolist() != ["Comodo", "Area (m2)", "Perimetro (m)", "Iluminacao (VA)", "Iluminacao Tipo", "TUG (Qtd)", "Potencia TUG (VA)", "TUE (Qtd)", "TUE (Watts)"]:
    st.session_state.dados_cargas = pd.DataFrame({
        "Comodo": ["Sala", "Cozinha", "Quarto 1", "Quarto 2", "Banheiro"],
        "Area (m2)": [15.0, 10.0, 12.0, 10.0, 4.5],
        "Perimetro (m)": [16.0, 13.0, 14.0, 13.0, 9.0],
        "Iluminacao (VA)": ["-", "-", "-", "-", "-"],
        "Iluminacao Tipo": ["-", "-", "-", "-", "-"],
        "TUG (Qtd)": [0, 0, 0, 0, 0],
        "Potencia TUG (VA)": [0.0, 0.0, 0.0, 0.0, 0.0],
        "TUE (Qtd)": [0, 0, 0, 0, 0],
        "TUE (Watts)": [0.0, 0.0, 0.0, 0.0, 5500.0]
    })

if 'lista_circuitos' not in st.session_state: st.session_state.lista_circuitos = []
if 'resumo_materiais' not in st.session_state: st.session_state.resumo_materiais = []

# --- 4. ESTRUTURA DE NAVEGAÇÃO (MENU ORIGINAL HORIZONTAL) ---
st.title("⚡ VoltSpec Pocket")

# Retornando para o menu original com ícones lado a lado
aba = st.radio(
    "", 
    [
        "⚙️ Perfil", "🏠 Cargas", "💡 Luminotecnica", "❄️ Climatização", 
        "☀️ Energia Solar", "📉 Economia", "⚡ Queda de Tensão", 
        "📐 Dimensionador", "💰 Orçamentos", "📦 Materiais", "🛒 Produtos"
    ],
    horizontal=True,
    label_visibility="collapsed"
)
st.divider()

# --- MÓDULO PERFIL ---
if aba == "⚙️ Perfil":
    st.header("⚙️ Configurações do Técnico")
    st.session_state.perfil['nome_empresa'] = st.text_input("Empresa:", value=st.session_state.perfil.get('nome_empresa', ''))
    st.session_state.perfil['crt']          = st.text_input("CRT/CFT:", value=st.session_state.perfil.get('crt', ''))
    st.session_state.perfil['telefone']     = st.text_input("WhatsApp:", value=st.session_state.perfil.get('telefone', ''))
    st.session_state.perfil['cnpj']          = st.text_input("CNPJ:", value=st.session_state.perfil.get('cnpj', ''))
    st.session_state.perfil['email_contato'] = st.text_input("E-mail Profissional:", value=st.session_state.perfil.get('email_contato', ''))
    st.session_state.perfil['endereco']      = st.text_input("Cidade/UF:", placeholder="Ex: Araxá - MG", value=st.session_state.perfil.get('endereco', ''))

    if st.button("💾 Salvar Dados Localmente"):
        st.success("Perfil salvo! Os próximos relatórios serão gerados com estes dados.")

# --- MÓDULO CARGAS ---
elif aba == "🏠 Cargas":
    st.header("📋 Dimensionamento Profissional (NBR 5410 + Materiais)")

    with st.expander("🔌 Configuração da Rede e Concessionária", expanded=True):
        concessionaria = st.selectbox("Selecione a Concessionária:", ["CEMIG (MG)", "CPFL (SP)", "ENEL (RJ/SP)", "EQUATORIAL", "Outra (Manual)"])
        sistema_eletrico = st.selectbox("Sistema Elétrico:", ["Monofásico 127V", "Bifásico 220V"], index=0)
        if sistema_eletrico == "Monofásico 127V":
            tensao_fase = 127
            tensao_fase_neutro = 127
        else:
            tensao_fase = 220
            tensao_fase_neutro = 220

    st.subheader("1. Entrada de Dados e Medidas")
    
    st.write("**Área (m²), Perímetro (m) e TUE - Watts**")
    df_editor = st.data_editor(
        st.session_state.dados_cargas[["Comodo", "Area (m2)", "Perimetro (m)", "TUE (Watts)"]],
        num_rows="dynamic",
        use_container_width=True,
        key="editor_cargas_v1",
        disabled=["Comodo"]
    )

    if st.button("⚡ Calcular Projeto e Dimensionar Circuitos", type="primary", use_container_width=True):
        st.session_state.dados_cargas = st.session_state.dados_cargas.iloc[:len(df_editor)].copy()
        
        st.session_state.dados_cargas["Area (m2)"] = df_editor["Area (m2)"].values
        st.session_state.dados_cargas["Perimetro (m)"] = df_editor["Perimetro (m)"].values
        st.session_state.dados_cargas["TUE (Watts)"] = df_editor["TUE (Watts)"].values
        
        df_calc = st.session_state.dados_cargas.copy()
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
                if a <= 0 or p <= 0: 
                    st.session_state.dados_cargas.at[i, "Iluminacao (VA)"] = "-"
                    st.session_state.dados_cargas.at[i, "Iluminacao Tipo"] = "-"
                    st.session_state.dados_cargas.at[i, "TUG (Qtd)"] = 0
                    st.session_state.dados_cargas.at[i, "Potencia TUG (VA)"] = 0.0
                    st.session_state.dados_cargas.at[i, "TUE (Qtd)"] = 0
                    continue
                
                nome = str(r["Comodo"]).lower()

                if a <= 6:
                    va_ilum = 100
                else:
                    va_ilum = 100 + (math.floor((a - 6) / 4) * 60)
                
                qtd_lamp = max(math.ceil(va_ilum / 100), 1)
                tipo_ilum = "LED" if qtd_lamp <= 3 else ("Fluorescente" if qtd_lamp <= 5 else "Mista")
                
                st.session_state.dados_cargas.at[i, "Iluminacao (VA)"] = f"{va_ilum}VA"
                st.session_state.dados_cargas.at[i, "Iluminacao Tipo"] = f"{qtd_lamp} pt {tipo_ilum}"
                pot_ilum_total += va_ilum

                comp_15 = p + (qtd_lamp * 3.5)
                cabos["1.5mm2"]["Fase"] += comp_15 * 1.5
                cabos["1.5mm2"]["Neutro"] += comp_15
                cabos["1.5mm2"]["Terra"] += comp_15

                is_molhada = any(x in nome for x in ["cozinha", "banheiro", "servico", "lavanderia", "copa", "wc"])
                is_banheiro = any(x in nome for x in ["banheiro", "wc", "suite"])

                if is_banheiro:
                    q_tugs = 1
                    p_tugs = 600
                else:
                    div = 3.5 if is_molhada else 5.0
                    q_tugs = max(math.ceil(p / div), 1)
                    
                    if is_molhada:
                        p_tugs = (min(q_tugs, 3) * 600 + max(0, q_tugs - 3) * 100)
                    else:
                        p_tugs = q_tugs * 100

                st.session_state.dados_cargas.at[i, "TUG (Qtd)"] = int(q_tugs)
                st.session_state.dados_cargas.at[i, "Potencia TUG (VA)"] = float(p_tugs)
                pot_tug_total += p_tugs

                comp_25 = p + (q_tugs * 1.5)
                cabos["2.5mm2"]["Fase"] += comp_25
                cabos["2.5mm2"]["Neutro"] += comp_25
                cabos["2.5mm2"]["Terra"] += comp_25

                tue_w = float(r["TUE (Watts)"] or 0)
                qtd_tue = 0
                
                if tue_w > 0:
                    if sistema_eletrico == "Monofásico 127V":
                        v_tue = 127
                    else:
                        v_tue = 220
                    
                    corrente = tue_w / v_tue
                    qtd_tue = 1
                    
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
                    
                    comp_tue = (p / 2) + 4.0
                    
                    if v_tue == 220 and sistema_eletrico == "Bifásico 220V":
                        cabos[bitola]["Fase"] += comp_tue * 2
                        cabos[bitola]["Neutro"] += 0
                        cabos[bitola]["Terra"] += comp_tue
                    else:
                        cabos[bitola]["Fase"] += comp_tue
                        cabos[bitola]["Neutro"] += comp_tue
                        cabos[bitola]["Terra"] += comp_tue

                st.session_state.dados_cargas.at[i, "TUE (Qtd)"] = int(qtd_tue)

            except Exception as e:
                continue

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

    st.subheader("2. Resultados Calculados")
    
    if st.session_state.get('lista_circuitos'):
        st.write("**Resumo de Cargas por Cômodo:**")
        df_resumo = st.session_state.dados_cargas[[
            "Comodo", "Area (m2)", "Perimetro (m)", "Iluminacao (VA)", 
            "Iluminacao Tipo", "TUG (Qtd)", "Potencia TUG (VA)", "TUE (Qtd)", "TUE (Watts)"
        ]].copy()
        
        st.dataframe(df_resumo, use_container_width=True)
    else:
        st.info("📊 Preencha os dados (Área, Perímetro e TUE) e clique em 'Calcular Projeto e Dimensionar Circuitos' para ver os resultados aqui.")
        df_resumo = st.session_state.dados_cargas[[
            "Comodo", "Area (m2)", "Perimetro (m)", "Iluminacao (VA)", 
            "Iluminacao Tipo", "TUG (Qtd)", "Potencia TUG (VA)", "TUE (Qtd)", "TUE (Watts)"
        ]].copy()
        st.dataframe(df_resumo, use_container_width=True)

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
                hoje = datetime.now()
                validade = hoje + timedelta(days=7)
                
                pdf = FPDF()
                pdf.add_page()
                
                # ===== CABEÇALHO =====
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 12, "MEMORIAL TECNICO - PROJETO ELETRICO", 0, 1, "C")
                pdf.set_fill_color(200, 200, 200)
                
                pdf.set_font("Arial", "I", 8)
                pdf.cell(0, 5, f"Gerado em: {hoje.strftime('%d/%m/%Y %H:%M')} | Valido ate: {validade.strftime('%d/%m/%Y')}", 0, 1, "R")
                pdf.ln(3)
                
                # ===== DADOS DO PROFISSIONAL/TÉCNICO =====
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 7, "DADOS DO PROFISSIONAL/TECNICO", 0, 1)
                pdf.set_font("Arial", "", 9)
                pdf.cell(60, 6, "Empresa:", 0, 0)
                pdf.cell(0, 6, st.session_state.perfil.get('nome_empresa', 'Nao informado'), 0, 1)
                pdf.cell(60, 6, "CRT/CFT:", 0, 0)
                pdf.cell(0, 6, st.session_state.perfil.get('crt', 'Nao informado'), 0, 1)
                pdf.cell(60, 6, "CNPJ:", 0, 0)
                pdf.cell(0, 6, st.session_state.perfil.get('cnpj', 'Nao informado'), 0, 1)
                pdf.cell(60, 6, "Telefone:", 0, 0)
                pdf.cell(0, 6, st.session_state.perfil.get('telefone', 'Nao informado'), 0, 1)
                pdf.cell(60, 6, "E-mail:", 0, 0)
                pdf.cell(0, 6, st.session_state.perfil.get('email_contato', 'Nao informado'), 0, 1)
                pdf.cell(60, 6, "Localidade:", 0, 0)
                pdf.cell(0, 6, st.session_state.perfil.get('endereco', 'Nao informado'), 0, 1)
                
                pdf.ln(5)

                # ===== CONFIGURAÇÃO DA INSTALAÇÃO =====
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 7, "CONFIGURACAO DA INSTALACAO", 0, 1)
                pdf.set_font("Arial", "", 9)
                pdf.cell(60, 6, "Concessionaria:", 0, 0)
                pdf.cell(0, 6, str(st.session_state.get('concessionaria', 'N/A')), 0, 1)
                pdf.cell(60, 6, "Sistema Eletrico:", 0, 0)
                pdf.cell(0, 6, str(st.session_state.get('sistema_eletrico', 'N/A')), 0, 1)
                pdf.cell(60, 6, "Norma Utilizada:", 0, 0)
                pdf.cell(0, 6, "NBR 5410 (Instalacoes Eletricas de Baixa Tensao)", 0, 1)
                
                pdf.ln(5)
                
                # ===== TABELA DE CARGAS =====
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 7, "1. MEMORIAL DE CARGAS", 0, 1)
                pdf.ln(2)
                
                pdf.set_font("Arial", "B", 8)
                pdf.set_fill_color(200, 200, 200)
                
                col_widths = [28, 14, 14, 16, 16, 14, 16, 12, 16]
                headers = ["Comodo", "Area", "Perim.", "Ilum.", "Tipo Ilum.", "TUGs", "Pot.TUG", "TUE", "Watts"]
                
                for header, width in zip(headers, col_widths):
                    pdf.cell(width, 7, header, 1, 0, "C", True)
                pdf.ln()
                
                pdf.set_font("Arial", "", 7)
                pdf.set_fill_color(255, 255, 255)
                
                for _, r in st.session_state.dados_cargas.iterrows():
                    pdf.cell(28, 6, str(r["Comodo"])[:13], 1)
                    pdf.cell(14, 6, f"{float(r['Area (m2)']):.1f}m2", 1, 0, "C")
                    pdf.cell(14, 6, f"{float(r['Perimetro (m)']):.1f}m", 1, 0, "C")
                    pdf.cell(16, 6, str(r["Iluminacao (VA)"])[:10], 1, 0, "C")
                    pdf.cell(16, 6, str(r["Iluminacao Tipo"])[:14], 1, 0, "C")
                    pdf.cell(14, 6, str(int(r["TUG (Qtd)"])), 1, 0, "C")
                    pdf.cell(16, 6, f"{float(r['Potencia TUG (VA)']):.0f}VA", 1, 0, "C")
                    pdf.cell(12, 6, str(int(r["TUE (Qtd)"])), 1, 0, "C")
                    pdf.cell(16, 6, f"{float(r['TUE (Watts)']):.0f}W", 1, 1, "C")
                
                pdf.ln(3)

                # ===== TABELA DE CIRCUITOS =====
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 7, "2. QUADRO DE CIRCUITOS (QDC)", 0, 1)
                pdf.ln(2)
                
                pdf.set_font("Arial", "B", 8)
                pdf.set_fill_color(200, 200, 200)
                
                circ_widths = [13, 28, 18, 13, 16, 13, 16, 13]
                circ_headers = ["Circ", "Descricao", "Potencia", "Tensao", "Corrente", "Cabo", "Disj.", "Tipo"]
                
                for header, width in zip(circ_headers, circ_widths):
                    pdf.cell(width, 7, header, 1, 0, "C", True)
                pdf.ln()
                
                pdf.set_font("Arial", "", 7)
                pdf.set_fill_color(255, 255, 255)
                
                for circ in st.session_state.lista_circuitos:
                    pdf.cell(13, 6, str(circ.get("Circ", "")), 1)
                    pdf.cell(28, 6, str(circ.get("Descricao", ""))[:18], 1, 0, "L")
                    pdf.cell(18, 6, str(circ.get("Potencia", "")), 1, 0, "C")
                    pdf.cell(13, 6, str(circ.get("Tensao", "")), 1, 0, "C")
                    pdf.cell(16, 6, str(circ.get("Corrente", ""))[:10], 1, 0, "C")
                    pdf.cell(13, 6, str(circ.get("Cabo", "")), 1, 0, "C")
                    pdf.cell(16, 6, str(circ.get("Disjuntor", "")), 1, 0, "C")
                    pdf.cell(13, 6, str(circ.get("Tipo Disj.", ""))[:8], 1, 1, "C")
                
                pdf.ln(3)
                
                # ===== TABELA DE MATERIAIS =====
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 7, "3. LISTA DE MATERIAIS", 0, 1)
                pdf.ln(2)
                
                pdf.set_font("Arial", "B", 8)
                pdf.set_fill_color(200, 200, 200)
                pdf.cell(140, 7, "Material", 1, 0, "L", True)
                pdf.cell(60, 7, "Quantidade", 1, 1, "C", True)
                
                pdf.set_font("Arial", "", 8)
                pdf.set_fill_color(255, 255, 255)
                
                for mat in st.session_state.resumo_materiais:
                    pdf.cell(140, 6, str(mat.get("Item", "")), 1)
                    pdf.cell(60, 6, str(mat.get("Qtd", "")), 1, 1, "C")
                
                # ===== NOTAS TÉCNICAS =====
                pdf.ln(5)
                pdf.set_font("Arial", "B", 9)
                pdf.cell(0, 7, "NOTAS TECNICAS:", 0, 1)
                pdf.set_font("Arial", "", 8)
                notas = [
                    "- Todos os calculos foram realizados conforme NBR 5410:2008",
                    "- As bitolas de cabo foram selecionadas com seguranca",
                    "- Os disjuntores sao de curva C (uso residencial/comercial)",
                    "- Considerar topico 6.4.3 da NBR 5410 para agrupamento de circuitos",
                    "- O projeto deve ser executado por eletricista registrado no CREA"
                ]
                for nota in notas:
                    pdf.multi_cell(0, 4, nota)
                
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
        
        if st.button("🔄 Limpar e Recalcular", use_container_width=True):
            st.session_state.lista_circuitos = None
            st.session_state.resumo_materiais = None
            st.session_state.dados_cargas = pd.DataFrame({
                "Comodo": ["Sala", "Cozinha", "Quarto 1", "Quarto 2", "Banheiro"],
                "Area (m2)": [15.0, 10.0, 12.0, 10.0, 4.5],
                "Perimetro (m)": [16.0, 13.0, 14.0, 13.0, 9.0],
                "Iluminacao (VA)": ["-", "-", "-", "-", "-"],
                "Iluminacao Tipo": ["-", "-", "-", "-", "-"],
                "TUG (Qtd)": [0, 0, 0, 0, 0],
                "Potencia TUG (VA)": [0.0, 0.0, 0.0, 0.0, 0.0],
                "TUE (Qtd)": [0, 0, 0, 0, 0],
                "TUE (Watts)": [0.0, 0.0, 0.0, 0.0, 5500.0]
            })
            st.rerun()

# --- MÓDULO Luminotecnica  ---
elif aba == "💡 Luminotecnica":
    st.header("💡 Dimensionamento Luminotécnico (NBR ISO/CIE 8995-1)")
    st.info("Este módulo utiliza o Método dos Lúmens para calcular a quantidade de luminárias necessária.")

    with st.expander("🏠 Dados do Ambiente", expanded=True):
        comprimento = st.number_input("Comprimento (m):", min_value=0.1, value=5.0, key="lum_comp")
        largura = st.number_input("Largura (m):", min_value=0.1, value=4.0, key="lum_larg")
        h_total = st.number_input("Pé direito total (m):", min_value=0.1, value=3.0, key="lum_h_total")
        h_trabalho = st.number_input("Altura do plano de trabalho (m):", min_value=0.0, value=0.75, help="Mesa: 0.75m | Chão: 0.0m", key="lum_h_trab")
        h_luminaria = st.number_input("Altura da luminária ao teto (m):", min_value=0.0, value=0.0, help="Embutida: 0.0m", key="lum_h_lum")
        
        h_util = h_total - h_trabalho - h_luminaria
        area_total = comprimento * largura
        st.write(f"**Área Total:** {area_total:.2f} m² | **Altura Útil (h):** {h_util:.2f} m")

    with st.expander("📚 Parâmetros Normativos"):
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

        fator_utilizacao = st.slider("Fator de Utilização (η):", 0.1, 1.0, 0.5, help="Depende da luminária e cores das paredes.", key="lum_fu")
        fator_perdas = st.select_slider("Fator de Manutenção (Limpeza):", options=[0.6, 0.7, 0.8], value=0.8, help="0.8: Limpo | 0.7: Médio | 0.6: Sujo", key="lum_fm")

    with st.expander("🔦 Especificações da Lâmpada/Luminária"):
        fluxo_unitario = st.number_input("Fluxo Luminoso por Luminária (Lúmens):", min_value=1, value=2500, help="Ver no catálogo do fabricante", key="lum_fluxo_u")
        potencia_unit = st.number_input("Potência por Luminária (W):", min_value=1, value=24, key="lum_pot_u")

    fluxo_total_necessario = (nivel_iluminancia * area_total) / (fator_utilizacao * fator_perdas)
    quantidade_n = fluxo_total_necessario / fluxo_unitario
    quantidade_final = int(-(-quantidade_n // 1))
    
    potencia_total = quantidade_final * potencia_unit
    densidade_potencia = potencia_total / area_total if area_total > 0 else 0

    st.subheader("📊 Resultado do Dimensionamento")
    res1, res2 = st.columns(2)
    res1.metric("Qtd. de Luminárias", f"{quantidade_final} un")
    res2.metric("Potência Total", f"{potencia_total} W")
    st.metric("Densidade", f"{densidade_potencia:.2f} W/m²")

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
        pdf_bytes = gerar_pdf_resultado_lumino(dados_atuais, st.session_state.get('perfil', {}))
        if pdf_bytes:
            st.download_button(
                label="📥 Gerar e Baixar Relatório (PDF)",
                data=pdf_bytes,
                file_name="Luminotecnico.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="btn_download_lumino"
            )
    except Exception as e:
        st.error(f"Erro ao preparar o PDF: {e}")

# --- MÓDULO CLIMATIZAÇÃO ---
elif aba == "❄️ Climatização":
    st.header("❄️ Dimensionamento e Sugestão de Aparelhos")
    st.info("Cálculo de carga térmica e curadoria dos melhores modelos do mercado.")

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
        area_clima = st.number_input("Área do Ambiente (m²):", min_value=1.0, value=15.0)
        exposicao_sol = st.selectbox("Exposição ao Sol:", ["Manhã ou Sombra (600 BTUs/m²)", "Tarde ou Sol Forte (800 BTUs/m²)"])
        num_pessoas = st.number_input("Número de Pessoas (além de você):", min_value=0, value=1)
        num_eletronicos = st.number_input("Número de Eletrônicos (TV, PC, etc):", min_value=0, value=1)

    fator_area = 800 if "Sol Forte" in exposicao_sol else 600
    btu_base = area_clima * fator_area
    btu_pessoas = num_pessoas * 600
    btu_aparelhos = num_eletronicos * 600
    total_btus = btu_base + btu_pessoas + btu_aparelhos

    comerciais = sorted(modelos_referencia.keys())
    sugestao_btu = comerciais[0]
    for c in comerciais:
        if c >= total_btus:
            sugestao_btu = c
            break
    
    modelo_nome = modelos_referencia.get(sugestao_btu, "Consulte um especialista para grandes áreas")

    st.divider()
    st.metric("Carga Térmica Total", f"{int(total_btus)} BTUs")
    st.metric("Capacidade Comercial", f"{sugestao_btu} BTUs", delta="Sugerido")

    st.success(f"🏆 **Modelos Recomendados (Linha Inverter):** \n\n {modelo_nome}")

    if st.button("📄 Gerar Relatório com Sugestão de Marcas", use_container_width=True):
        try:
            pdf = FPDF()
            pdf.add_page()
            montar_cabecalho_pdf(pdf, st.session_state.perfil)

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "RELATORIO DE DIMENSIONAMENTO E COMPRA", "B", 1, "C")
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, "1. Detalhes do Ambiente", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, f"- Area: {area_clima} m2 | Carga Calculada: {int(total_btus)} BTUs", 0, 1)
            pdf.cell(0, 6, f"- Fator Solar: {exposicao_sol}", 0, 1)

            pdf.ln(5)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "2. Recomendacao de Equipamento", 0, 1)
            
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, f"Capacidade Necessaria: {sugestao_btu} BTUs", 1, 1, "C", True)
            
            pdf.ln(2)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 8, "Marcas e Modelos Sugeridos (Alta Eficiencia):", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 8, f"{modelo_nome}", 1, "C")

            pdf.ln(10)
            pdf.set_font("Arial", "I", 9)
            pdf.multi_cell(0, 5, "Nota Tecnica: Recomendamos a instalacao de modelos com tecnologia INVERTER "
                               "para economia de ate 70% na conta de luz. A instalacao deve seguir as "
                               "normas do fabricante para preservacao da garantia.")

            pdf_output = pdf.output(dest="S").encode("latin-1", "ignore")
            st.download_button("⬇️ Baixar Relatório de Compra", pdf_output, "Guia_Compra_Ar.pdf", "application/pdf", use_container_width=True)
            
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

# --- MÓDULO ENERGIA SOLAR ---
elif aba == "☀️ Energia Solar":
    st.header("☀️ Estimativa Solar Fotovoltaica")
    st.info("Gere uma estimativa rápida de investimento e economia para sistemas On-Grid.")

    with st.expander("📊 Dados de Consumo e Local", expanded=True):
        consumo_kwh = st.number_input("Consumo Médio Mensal (kWh):", min_value=50.0, value=400.0, step=10.0)
        tarifa_energia = st.number_input("Preço do kWh (com impostos - R$):", min_value=0.1, value=0.95, step=0.01)
        potencia_painel = st.selectbox("Potência do Painel (Watts):", [450, 550, 600, 650], index=1)
        eficiencia_sistema = 0.80

    hsp_araxa = 5.2 
    potencia_necessaria_kwp = consumo_kwh / (30 * hsp_araxa * eficiencia_sistema)
    
    qtd_paineis = math.ceil((potencia_necessaria_kwp * 1000) / potencia_painel)
    potencia_real_instalada = (qtd_paineis * potencia_painel) / 1000
    area_estimada = qtd_paineis * 2.6
    investimento_estimado = potencia_real_instalada * 1000 * 3.80
    economia_mensal = consumo_kwh * tarifa_energia
    payback_meses = investimento_estimado / economia_mensal if economia_mensal > 0 else 0

    st.divider()
    res1, res2 = st.columns(2)
    res1.metric("Painéis Necessários", f"{qtd_paineis} un")
    res2.metric("Potência do Sistema", f"{potencia_real_instalada:.2f} kWp")
    st.metric("Área no Telhado", f"{area_estimada:.1f} m²")

    st.metric("Investimento Estimado", f"R$ {investimento_estimado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.metric("Payback (Retorno)", f"{math.ceil(payback_meses/12)} anos", f"{int(payback_meses)} meses")

    if st.button("📄 Gerar Estudo de Viabilidade Solar (PDF)", use_container_width=True):
        try:
            pdf = FPDF()
            pdf.add_page()
            montar_cabecalho_pdf(pdf, st.session_state.perfil)

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "ESTUDO PRELIMINAR DE VIABILIDADE SOLAR", "B", 1, "C")
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "1. Resumo do Dimensionamento", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, f"- Consumo Mensal Alvo: {consumo_kwh} kWh", 0, 1)
            pdf.cell(0, 7, f"- Potencia Geradora Recomendada: {potencia_real_instalada:.2f} kWp", 0, 1)
            pdf.cell(0, 7, f"- Quantidade de Modulos ({potencia_painel}W): {qtd_paineis} unidades", 0, 1)
            pdf.cell(0, 7, f"- Espaco Necessario em Telhado: {area_estimada:.1f} m2", 0, 1)

            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "2. Analise Financeira Estimada", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, f"- Investimento Aproximado: R$ {investimento_estimado:,.2f}", 0, 1)
            pdf.cell(0, 7, f"- Economia Mensal Estimada: R$ {economia_mensal:,.2f}", 0, 1)
            pdf.cell(0, 7, f"- Tempo de Retorno (Payback): aprox. {math.ceil(payback_meses/12)} anos", 0, 1)

            pdf.ln(10)
            pdf.set_fill_color(230, 230, 230)
            pdf.set_font("Arial", "I", 9)
            pdf.multi_cell(0, 5, "AVISO: Este relatorio e uma estimativa baseada na media de radiacao solar da regiao. "
                               "Os valores de investimento podem variar conforme a marca dos equipamentos, tipo de telhado e "
                               "distancia do quadro de energia. Requer visita tecnica e projeto executivo.", 1, "J", True)

            pdf_output = pdf.output(dest="S").encode("latin-1", "ignore")
            st.download_button("⬇️ Baixar Estudo Solar", pdf_output, "Estudo_Solar_VoltSpec.pdf", "application/pdf", use_container_width=True)
            
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

# --- MÓDULO SIMULADOR DE ECONOMIA ---
elif aba == "📉 Economia":
    st.header("📉 Simulador de Economia de Energia")

    with st.expander("💡 Modernização de Iluminação", expanded=True):
        tipo_antiga = st.selectbox("Tipo de Lâmpada Atual:", ["Incandescente (60W)", "Fluorescente (40W)"])
        qtd_lampadas = st.number_input("Quantidade de Lâmpadas:", min_value=1, value=10)
        horas_uso = st.number_input("Horas de uso por dia:", min_value=1, max_value=24, value=6)
        tarifa_simulada = st.number_input("Tarifa de Energia (R$/kWh):", value=0.95, key="tarifa_eco")

    watts_antiga = 60 if "Incandescente" in tipo_antiga else 40
    watts_nova = 9 if "Incandescente" in tipo_antiga else 18
    
    consumo_mensal_antigo = (watts_antiga * qtd_lampadas * horas_uso * 30) / 1000
    consumo_mensal_novo = (watts_nova * qtd_lampadas * horas_uso * 30) / 1000
    economia_kwh_mes = consumo_mensal_antigo - consumo_mensal_novo
    economia_rs_mes = economia_kwh_mes * tarifa_simulada

    st.divider()
    
    with st.expander("❄️ Upgrade para Ar-Condicionado Inverter"):
        btu_ar = st.selectbox("Potência do Aparelho (BTUs):", [9000, 12000, 18000, 24000])
        dias_uso_mes = st.slider("Dias de uso no mês:", 1, 30, 22)
        horas_ar = st.slider("Horas por dia:", 1, 24, 8)
    
    consumo_ref_hora = (btu_ar / 9000) * 1.0 
    consumo_ar_conv = consumo_ref_hora * horas_ar * dias_uso_mes
    economia_ar_rs = (consumo_ar_conv * 0.40) * tarifa_simulada 

    st.subheader("💰 Potencial de Economia Total")
    total_eco_mes = economia_rs_mes + economia_ar_rs
    total_eco_ano = total_eco_mes * 12

    res_e1, res_e2 = st.columns(2)
    res_e1.metric("Economia Mensal Estimada", f"R$ {total_eco_mes:.2f}")
    res_e2.metric("Economia Anual Estimada", f"R$ {total_eco_ano:.2f}", delta="Redução de Custos")

    if st.button("📄 Gerar Laudo de Economia (PDF)", use_container_width=True):
        try:
            pdf = FPDF()
            pdf.add_page()
            montar_cabecalho_pdf(pdf, st.session_state.perfil)

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "LAUDO TECNICO DE POTENCIAL DE ECONOMIA", "B", 1, "C")
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "1. Modernizacao da Iluminacao", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, f"- Troca de {qtd_lampadas} unidades de lampadas {tipo_antiga} por LED.", 0, 1)
            pdf.cell(0, 7, f"- Reducao mensal de consumo: {economia_kwh_mes:.2f} kWh", 0, 1)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 7, f"- Economia financeira em iluminacao: R$ {economia_rs_mes:.2f}/mes", 0, 1)

            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "2. Eficiencia em Climatizacao (Inverter)", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, f"- Upgrade para tecnologia Inverter em aparelho de {btu_ar} BTUs.", 0, 1)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 7, f"- Economia financeira em climatizacao: R$ {economia_ar_rs:.2f}/mes", 0, 1)

            pdf.ln(10)
            pdf.set_fill_color(0, 128, 0)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 12, f"ECONOMIA TOTAL ESTIMADA: R$ {total_eco_ano:.2f} POR ANO", 0, 1, "C", True)
            
            pdf.set_text_color(0, 0, 0)
            pdf.ln(5)
            pdf.set_font("Arial", "I", 9)
            pdf.multi_cell(0, 5, "Nota: Este simulador utiliza medias de consumo baseadas em especificacoes tecnicas de fabricantes. "
                               "A economia real pode variar de acordo com a marca dos equipamentos e habitos de uso.")

            pdf_output = pdf.output(dest="S").encode("latin-1", "ignore")
            st.download_button("⬇️ Baixar Laudo de Economia", pdf_output, "Laudo_Economia_VoltSpec.pdf", "application/pdf", use_container_width=True)
            
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")

# --- MÓDULO ORÇAMENTOS ---
elif aba == "💰 Orçamentos":
    st.header("💰 Orçamentos de Serviços")
    cliente = st.text_input("Nome do Cliente:", "Cliente")
    servicos = [
        {"Descricao": "Ponto de Tomada / Interruptor", "Qtd": 0, "Preco": 85.0},
        {"Descricao": "Ponto de Iluminacao",            "Qtd": 0, "Preco": 75.0},
        {"Descricao": "Montagem de Quadro (ate 12 disj.)",    "Qtd": 0, "Preco": 450.0},
        {"Descricao": "Montagem de Quadro (acima 12 disj.)",  "Qtd": 0, "Preco": 650.0},
        {"Descricao": "Padrao CEMIG Monofasico",        "Qtd": 0, "Preco": 850.0},
        {"Descricao": "Padrao CEMIG Trifasico",          "Qtd": 0, "Preco": 1350.0},
        {"Descricao": "Instalacao de Chuveiro",         "Qtd": 0, "Preco": 110.0},
        {"Descricao": "Laudo de Conformidade",           "Qtd": 0, "Preco": 350.0}
    ]
    df_serv = st.data_editor(pd.DataFrame(servicos), num_rows="dynamic", use_container_width=True, key="orc_edt")

    total_orc = (df_serv["Qtd"] * df_serv["Preco"]).sum()
    st.subheader(f"Total Serviços: R$ {total_orc:,.2f}")

    if st.button("📄 Gerar PDF Orçamento", use_container_width=True):
        pdf = gerar_pdf_universal(f"ORCAMENTO - {cliente}", df_serv, [100, 20, 35, 35], ["Descricao", "Qtd", "Unit.", "Subtotal"])
        if pdf:
            st.download_button("⬇️ Baixar PDF", pdf, "Orcamento.pdf", "application/pdf", use_container_width=True)

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

    if st.button("📄 Gerar PDF Materiais", use_container_width=True):
        pdf = gerar_pdf_universal("LISTA DE MATERIAIS", df_mat, [100, 20, 35, 35], ["Descricao", "Qtd", "Unit.", "Subtotal"])
        if pdf:
            st.download_button("⬇️ Baixar PDF", pdf, "Materiais.pdf", "application/pdf", use_container_width=True)
           
# --- MÓDULO QUEDA DE TENSÃO REAL ---
elif aba == "⚡ Queda de Tensão":
    st.header("⚡ Diagnóstico de Queda de Tensão (NBR 5410)")

    with st.expander("🔌 Dados da Instalação", expanded=True):
        v_nominal = st.selectbox("Tensão Nominal (V):", [127, 220, 380, 440])
        corrente_a = st.number_input("Corrente Medida/Carga (A):", min_value=0.1, value=10.0)
        distancia_m = st.number_input("Distância do Cabo (metros):", min_value=1.0, value=20.0)
        secao_cabo = st.selectbox("Seção do Cabo Atual (mm²):", [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50])
        material_cabo = st.radio("Material do Condutor:", ["Cobre", "Alumínio"], horizontal=True)
        fase_sistema = st.radio("Tipo de Circuito:", ["Monofásico/Bifásico", "Trifásico"], horizontal=True)

    rho = 0.0172 if material_cabo == "Cobre" else 0.0282
    k = 2 if fase_sistema == "Monofásico/Bifásico" else 1.732 
    
    queda_volts = (k * rho * distancia_m * corrente_a) / secao_cabo
    queda_percentual = (queda_volts / v_nominal) * 100
    v_final = v_nominal - queda_volts

    limite_norma = 4.0
    esta_dentro = queda_percentual <= limite_norma

    st.divider()
    res1, res2 = st.columns(2)
    res1.metric("Queda em Volts", f"{queda_volts:.2f} V")
    
    if esta_dentro:
        res2.metric("Queda Percentual", f"{queda_percentual:.2f} %", "✅ Dentro da Norma", delta_color="normal")
    else:
        res2.metric("Queda Percentual", f"{queda_percentual:.2f} %", "⚠️ Fora da Norma", delta_color="inverse")
        
    st.metric("Tensão na Carga", f"{v_final:.1f} V")

    if not esta_dentro:
        st.warning(f"🚨 **Atenção:** A queda de tensão ultrapassou os {limite_norma}% recomendados pela NBR 5410. Isso causa aquecimento dos cabos, desperdício de energia e pode danificar motores e eletrônicos.")
    else:
        st.success("✅ A fiação está adequadamente dimensionada para esta distância e carga.")

    if st.button("📄 Gerar Laudo de Conformidade (PDF)", use_container_width=True):
        try:
            pdf = FPDF()
            pdf.add_page()
            montar_cabecalho_pdf(pdf, st.session_state.perfil)

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "LAUDO TECNICO DE QUEDA DE TENSAO", "B", 1, "C")
            
            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "1. Parametros Analisados", 0, 1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 7, f"- Tensao de Origem: {v_nominal}V | Circuito: {fase_sistema}", 0, 1)
            pdf.cell(0, 7, f"- Condutor: {secao_cabo}mm2 em {material_cabo}", 0, 1)
            pdf.cell(0, 7, f"- Comprimento do Trecho: {distancia_m} metros", 0, 1)
            pdf.cell(0, 7, f"- Corrente de Projeto: {corrente_a} A", 0, 1)

            pdf.ln(5)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, "2. Resultados do Diagnostico", 0, 1)
            pdf.set_font("Arial", "B", 12)
            
            status_texto = "CONFORME (DENTRO DA NORMA)" if esta_dentro else "NAO CONFORME (FORA DA NORMA)"
            pdf.cell(0, 10, f"STATUS: {status_texto}", 1, 1, "C")
            
            pdf.set_font("Arial", "", 10)
            pdf.ln(2)
            pdf.cell(0, 7, f"- Queda de Tensao Calculada: {queda_volts:.2f} V", 0, 1)
            pdf.cell(0, 7, f"- Percentual de Perda: {queda_percentual:.2f}% (Limite NBR 5410: {limite_norma}%)", 0, 1)
            pdf.cell(0, 7, f"- Tensao Final Disponivel no Equipamento: {v_final:.1f} V", 0, 1)

            if not esta_dentro:
                pdf.ln(5)
                pdf.set_text_color(200, 0, 0)
                pdf.set_font("Arial", "B", 10)
                pdf.multi_cell(0, 6, "RECOMENDACAO TECNICA: E necessaria a substituicao dos condutores por uma secao superior "
                                   "ou a redistribuicao das cargas para reduzir a distancia do circuito, visando evitar "
                                   "sobreaquecimento e perda de eficiencia energetica.")
            
            pdf.set_text_color(0, 0, 0)
            pdf_output = pdf.output(dest="S").encode("latin-1", "ignore")
            st.download_button("⬇️ Baixar Laudo de Diagnóstico", pdf_output, "Laudo_Tecnico_Queda_Tensao.pdf", "application/pdf", use_container_width=True)
            
        except Exception as e:
             st.error(f"Erro ao gerar PDF: {e}")

# --- MÓDULO DIMENSIONADOR ---
elif aba == "📐 Dimensionador":
    st.header("📐 Cálculo Técnico Profissional (NBR 5410)")

    pot        = st.number_input("Potência Total (W):", value=1200.0, step=100.0)
    tipo_carga = st.selectbox("Tipo de Carga:", ["Iluminação", "Tomadas (Geral/TUE)"])
    tensao     = st.selectbox("Tensão (V):", [127, 220])
    dist       = st.number_input("Distância do Quadro (m):", value=15.0, step=1.0)
    fator_agrup = st.slider("Fator de Agrupamento:", 0.4, 1.0, 1.0, help="0.70 para 3 circuitos no mesmo conduíte")

    ib = pot / tensao if tensao > 0 else 0
    ib_corrigida = ib / fator_agrup if fator_agrup > 0 else 0
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
    c_res1, c_res2 = st.columns(2)
    with c_res1:
        st.metric("Corrente de Projeto (Ib)", f"{ib:.2f} A")
        if fator_agrup < 1:
            st.caption(f"Ib Corrigida (Agrup.): {ib_corrigida:.2f} A")
        st.metric("Bitola Final", f"{bitola_final} mm²")
    with c_res2:
        color = "normal" if percentual_queda <= 4.0 else "inverse"
        st.metric("Queda de Tensão", f"{percentual_queda:.2f} %", delta=f"{queda_v:.2f} V", delta_color=color)

    st.subheader("🕳️ Ocupação do Eletroduto")
    
    area_cabos = {1.5: 6.0, 2.5: 7.5, 4.0: 11.0, 6.0: 14.5, 10.0: 22.5}
    area_eletrodutos = {"20mm (1/2\")": 176, "25mm (3/4\")": 283, "32mm (1\")": 530, "40mm (1 1/4\")": 907}

    qtd_condutores = st.number_input("Qtd. de Condutores no Trecho:", min_value=1, value=3, step=1, help="Ex: Fase + Neutro + Terra")
    eletroduto_escolhido = st.selectbox("Tamanho do Eletroduto:", list(area_eletrodutos.keys()))

    area_unitaria_cabo = area_cabos.get(bitola_final, bitola_final * 2.5) 
    area_total_cabos = area_unitaria_cabo * qtd_condutores
    area_eletroduto = area_eletrodutos[eletroduto_escolhido]
    
    if area_eletroduto > 0:
        taxa_ocupacao = (area_total_cabos / area_eletroduto) * 100
    else:
        taxa_ocupacao = 0

    if qtd_condutores == 1:
        limite_ocupacao = 53
    elif qtd_condutores == 2:
        limite_ocupacao = 31
    else:
        limite_ocupacao = 40

    cor_barra = "green" if taxa_ocupacao <= limite_ocupacao else "red"
    st.progress(min(taxa_ocupacao / 100, 1.0))
    st.caption(f"Ocupação atual: **{taxa_ocupacao:.1f}%** | Limite NBR 5410: **{limite_ocupacao}%**")
 
    st.subheader("🛡️ Verificação de Conformidade")
    erros, avisos = [], []
    
    if bitola_sugerida < bitola_minima:
        avisos.append(f"A norma exige mínimo de {bitola_minima}mm² para {tipo_carga.lower()}.")
    if percentual_queda > 4.0:
        erros.append("Queda de tensão acima de 4% (Limite NBR 5410 para circuitos terminais).")
        
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
    
    for p in prods:
        html_img = f"""
        <div style="background-color: white; border-radius: 10px; padding: 10px; display: flex; justify-content: center; align-items: center; height: 160px; margin-bottom: 10px;">
            <img src="{p['img']}" style="max-width: 100%; max-height: 100%; object-fit: contain;">
        </div>
        """
        st.markdown(html_img, unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: center; font-size: 14px; margin-bottom: 10px;'><b>{p['nome']}</b></div>", unsafe_allow_html=True)
        st.link_button("🚀 Ver Oferta", p["link"], use_container_width=True)
        st.divider()

# --- 8. RODAPÉ ---
st.markdown("---")
st.caption(f"📍 {st.session_state.perfil.get('endereco', 'Araxá - MG')}")
st.caption("⚡ Ferramenta de Bolso Pessoal")