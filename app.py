import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
import json

st.set_page_config(page_title="Fair Value - Sistema Universal", layout="wide")

def carregar_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        # Configuração de emergência caso o JSON falhe
        return {"bancos": [{"nome": "PADRAO", "identificador": "DEFAULT", "colunas": {"data": 0, "historico": 1, "valor": 2}}], "categorias": {}}

st.title("🏦 Extrator Fair Value: Multi-Banco")

arquivo_pdf = st.file_uploader("Selecione o Extrato Bancário (PDF)", type="pdf")

if arquivo_pdf:
    config = carregar_config()
    linhas_originais = []
    
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        # Lê a primeira página para identificar o banco pelo cabeçalho
        texto_capa = pdf.pages[0].extract_text().upper() if pdf.pages[0].extract_text() else ""
        
        # Busca o banco no JSON. Se não achar, usa o último (PADRAO)
        banco = config['bancos'][-1]
        for b in config['bancos']:
            if b['identificador'] in texto_capa:
                banco = b
                break
        
        for pagina in pdf.pages:
            tabela = pagina.extract_table({"vertical_strategy": "text", "horizontal_strategy": "lines", "intersection_y_tolerance": 3})
            if tabela:
                for linha in tabela:
                    dados = [str(c).replace('\n', ' ').strip() if c else "" for c in linha]
                    if any(dados):
                        linhas_originais.append(dados)

    if linhas_originais:
        df_bruto = pd.DataFrame(linhas_originais)
        st.subheader(f"🔍 Banco Detectado: {banco['nome']}")
        
        idx_data = banco['colunas']['data']
        idx_hist = banco['colunas']['historico']
        idx_valor = banco['colunas']['valor'] if banco['colunas']['valor'] < len(df_bruto.columns) else len(df_bruto.columns)-1

        if st.button("🚀 PROCESSAR EXTRATO"):
            final_data = []
            
            for i in range(len(df_bruto)):
                data = df_bruto.iloc[i, idx_data]
                hist = df_bruto.iloc[i, idx_hist]
                valor = df_bruto.iloc[i, idx_valor]
                
                # Identifica se a linha tem uma data (Início de uma transação)
                if re.search(r'\d{2}/', data):
                    final_data.append({"DATA": data, "HISTORICO": hist, "VALOR_ORIGINAL": valor})
                # Se não tem data, mas tem texto, concatena no histórico da transação anterior
                elif hist and len(final_data) > 0:
                    final_data[-1]["HISTORICO"] += " " + hist
                    if not final_data[-1]["VALOR_ORIGINAL"] and valor:
                        final_data[-1]["VALOR_ORIGINAL"] = valor

            if final_data:
                df_temp = pd.DataFrame(final_data)

                def limpar_e_categorizar(row):
                    v_bruto = str(row['VALOR_ORIGINAL']).upper()
                    indicativo = "D" if "D" in v_bruto or "-" in v_bruto else "C"
                    valor_num = re.sub(r'[^\d,.]', '', v_bruto)
                    
                    h_upper = str(row['HISTORICO']).upper()
                    cat = "Não Identificado"
                    for chave, valor_cat in config.get('categorias', {}).items():
                        if chave.upper() in h_upper:
                            cat = valor_cat
                            break
                    return pd.Series([valor_num, indicativo, cat])

                df_temp[['VALOR', 'INDICATIVO', 'CATEGORIA']] = df_temp.apply(limpar_e_categorizar, axis=1)
                
                # --- CORREÇÃO DO ERRO AQUI (.str.contains) ---
                df_final = df_temp[~df_temp['HISTORICO'].str.upper().str.contains("SALDO DO DIA", na=False)]
                # ---------------------------------------------
                
                df_final = df_final[['DATA', 'HISTORICO', 'VALOR', 'INDICATIVO', 'CATEGORIA']]

                st.success(f"✅ Extrato do {banco['nome']} processado com sucesso!")
                st.dataframe(df_final, use_container_width=True)
                
                csv = df_final.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(f"📥 Baixar CSV {banco['nome']}", csv, "extrato_fairvalue.csv", "text/csv")
            else:
                st.warning("Nenhuma transação válida encontrada com os critérios atuais.")
