import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="Fair Value - Extrator Bancário", layout="wide")

st.title("🏦 Extrator Fair Value: Extração Integral")

arquivo_pdf = st.file_uploader("Selecione o Extrato Bancário (PDF)", type="pdf")

if arquivo_pdf:
    dados_brutos = []
    
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        for pagina in pdf.pages:
            # Extração de tabelas com configuração de detecção de linhas
            tabelas = pagina.extract_tables({
                "vertical_strategy": "lines", 
                "horizontal_strategy": "text",
                "snap_tolerance": 3,
            })
            
            # Se não achar tabelas por linhas, tenta por texto
            if not tabelas:
                tabelas = pagina.extract_tables()
                
            for tabela in tabelas:
                for linha in tabela:
                    # Limpa apenas espaços vazios e converte para texto
                    linha_limpa = [str(c).replace('\n', ' ').strip() if c else "" for c in linha]
                    if any(linha_limpa):
                        dados_brutos.append(linha_limpa)

    if dados_brutos:
        df_b = pd.DataFrame(dados_brutos)

        st.subheader("🔍 1. Print do Extrato (Verificação)")
        st.info("Abaixo estão os dados capturados. Identifique os números das colunas.")
        st.dataframe(df_b.head(100), use_container_width=True)

        st.markdown("### ⚙️ 2. Calibração")
        col1, col2, col3 = st.columns(3)
        with col1: c_data = st.number_input("Nº coluna DATA", min_value=0, value=0)
        with col2: c_desc = st.number_input("Nº coluna HISTÓRICO", min_value=0, value=2)
        with col3: c_valor = st.number_input("Nº coluna VALOR", min_value=0, value=len(df_b.columns)-1)

        if st.button("🚀 PROCESSAR TUDO"):
            try:
                # Extração Total sem filtros
                df_f = df_b.iloc[:, [c_data, c_desc, c_valor]].copy()
                df_f.columns = ['DATA', 'HISTORICO', 'VALOR_BRUTO']

                # Lógica de Indicativo C/D
                def separar_financeiro(v_bruto):
                    v = str(v_bruto).upper()
                    if not v.strip() or v == "NONE": return pd.Series(["", ""])
                    
                    indicativo = "D" if "-" in v or "D" in v else "C"
                    valor_num = re.sub(r'[^\d,.]', '', v)
                    return pd.Series([valor_num, indicativo])

                df_f[['VALOR', 'INDICATIVO']] = df_f['VALOR_BRUTO'].apply(separar_financeiro)
                
                df_final = df_f[['DATA', 'HISTORICO', 'VALOR', 'INDICATIVO']].reset_index(drop=True)

                st.success("✅ Extração integral concluída!")
                st.dataframe(df_final, use_container_width=True)

                csv = df_final.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 Baixar CSV Total", csv, "extrato_total_fairvalue.csv", "text/csv")

            except Exception as e:
                st.error(f"Erro: {e}")
    else:
        st.error("O sistema não conseguiu detectar dados neste PDF. Tente um extrato original (não escaneado).")
