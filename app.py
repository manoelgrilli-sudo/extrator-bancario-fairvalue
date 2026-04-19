import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
import json

st.set_page_config(page_title="Fair Value - Auditoria Inteligente", layout="wide")

def carregar_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"bancos": [{"nome": "PADRAO", "identificador": "DEFAULT", "colunas": {"data": 0, "historico": 1, "valor": 2}}], "categorias": {}}

st.title("🏦 Extrator Fair Value: Ajuste de Precisão")

arquivo_pdf = st.file_uploader("Selecione o Extrato Bancário (PDF)", type="pdf")

if arquivo_pdf:
    config = carregar_config()
    linhas_brutas = []
    
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        texto_capa = pdf.pages[0].extract_text().upper()
        banco_detectado = next((b for b in config['bancos'] if b['identificador'] in texto_capa), config['bancos'][-1])
        
        for pagina in pdf.pages:
            tabela = pagina.extract_table({"vertical_strategy": "text", "horizontal_strategy": "lines", "intersection_y_tolerance": 3})
            if tabela:
                for linha in tabela:
                    linha_limpa = [str(c).replace('\n', ' ').strip() if c else "" for c in linha]
                    if any(linha_limpa):
                        linhas_brutas.append(linha_limpa)

    if linhas_brutas:
        df_b = pd.DataFrame(linhas_brutas)
        st.subheader(f"🔍 Banco: {banco_detectado['nome']}")
        
        c_data_idx = banco_detectado['colunas']['data']
        c_hist_idx = banco_detectado['colunas']['historico']
        c_valor_idx = banco_detectado['colunas']['valor'] if banco_detectado['colunas']['valor'] < len(df_b.columns) else len(df_b.columns)-1

        if st.button("🚀 PROCESSAR COM SOLDAGEM DE LINHAS"):
            processados = []
            
            # LÓGICA DE SOLDAGEM: Junta linhas sem data à linha anterior
            for i in range(len(df_b)):
                data = df_b.iloc[i, c_data_idx]
                hist = df_b.iloc[i, c_hist_idx]
                valor = df_b.iloc[i, c_valor_idx]
                
                # Se tem data, é um novo lançamento
                if re.search(r'\d{2}/\d{2}', data):
                    processados.append([data, hist, valor])
                # Se NÃO tem data mas tem histórico, junta com o de cima
                elif hist and len(processados) > 0:
                    processados[-1][1] += " " + hist
                    if not processados[-1][2] and valor:
                        processados[-1][2] = valor
            
            df_f = pd.DataFrame(processados, columns=['DATA', 'HISTORICO', 'VALOR_BRUTO'])

            def categorizar(row):
                v = str(row['VALOR_BRUTO']).upper()
                sinal = "D" if "-" in v or "D" in v else "C"
                valor_num = re.sub(r'[^\d,.]', '', v)
                
                h_upper = str(row['HISTORICO']).upper()
                cat = "Não Identificado"
                for chave, valor_cat in config.get('categorias', {}).items():
                    if chave.upper() in h_upper:
                        cat = valor_cat
                        break
                return pd.Series([valor_num, sinal, cat])

            df_f[['VALOR', 'INDICATIVO', 'CATEGORIA']] = df_f.apply(categorizar, axis=1)
            df_final = df_f[['DATA', 'HISTORICO', 'VALOR', 'INDICATIVO', 'CATEGORIA']]

            st.success("✅ Processamento concluído com as linhas corrigidas!")
            st.dataframe(df_final, use_container_width=True)
            
            csv = df_final.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Baixar CSV Corrigido", csv, "extrato_fairvalue_corrigido.csv", "text/csv")
