import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
import json

st.set_page_config(page_title="Fair Value - Ajuste Final Sicoob", layout="wide")

def carregar_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"bancos": [{"nome": "SICOOB", "identificador": "SICOOB", "colunas": {"data": 0, "historico": 2, "valor": 3}}], "categorias": {}}

st.title("🏦 Extrator Fair Value: Precisão Sicoob")

arquivo_pdf = st.file_uploader("Selecione o Extrato Bancário (PDF)", type="pdf")

if arquivo_pdf:
    config = carregar_config()
    linhas_originais = []
    
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        texto_completo = pdf.pages[0].extract_text().upper()
        banco = next((b for b in config['bancos'] if b['identificador'] in texto_completo), config['bancos'][0])
        
        for pagina in pdf.pages:
            tabela = pagina.extract_table({"vertical_strategy": "text", "horizontal_strategy": "lines", "intersection_y_tolerance": 3})
            if tabela:
                for linha in tabela:
                    # Limpa a linha e remove None
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
                
                # Se tem formato de data (ex: 10/mar), é uma nova linha de transação
                if re.search(r'\d{2}/[a-zA-Z]{3}', data) or re.search(r'\d{2}/\d{2}', data):
                    final_data.append({"DATA": data, "HISTORICO": hist, "VALOR_ORIGINAL": valor})
                
                # Se NÃO tem data e NÃO tem valor, mas tem texto no histórico, 
                # é o nome do cliente que quebrou para a linha de BAIXO.
                elif not data and not valor and hist and len(final_data) > 0:
                    final_data[-1]["HISTORICO"] += " " + hist
                
                # Se NÃO tem data mas TEM valor, tenta associar à transação atual
                elif not data and valor and len(final_data) > 0:
                    final_data[-1]["VALOR_ORIGINAL"] = valor

            df_processado = pd.DataFrame(final_data)

            # Função de Limpeza e Categorização
            def limpar_e_categorizar(row):
                v_bruto = str(row['VALOR_ORIGINAL']).upper()
                indicativo = "D" if "D" in v_bruto or "-" in v_bruto else "C"
                valor_limpo = re.sub(r'[^\d,.]', '', v_bruto)
                
                h_upper = str(row['HISTORICO']).upper()
                cat = "Não Identificado"
                for chave, valor_cat in config.get('categorias', {}).items():
                    if chave.upper() in h_upper:
                        cat = valor_cat
                        break
                return pd.Series([valor_limpo, indicativo, cat])

            df_processado[['VALOR', 'INDICATIVO', 'CATEGORIA']] = df_processado.apply(limpar_e_categorizar, axis=1)
            
            # Filtro para remover linhas de "Saldo do Dia" que poluem o faturamento
            df_final = df_processado[~df_processado['HISTORICO'].str.upper().contains("SALDO DO DIA")]
            df_final = df_final[['DATA', 'HISTORICO', 'VALOR', 'INDICATIVO', 'CATEGORIA']]

            st.success("✅ Extrato sincronizado com sucesso!")
            st.dataframe(df_final, use_container_width=True)
            
            csv = df_final.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Baixar CSV Corrigido", csv, "extrato_fairvalue_sincronizado.csv", "text/csv")
