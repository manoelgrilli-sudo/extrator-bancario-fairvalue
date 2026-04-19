import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="Fair Value - Extrator Inteligente", layout="wide")

st.title("🏦 Extrator Fair Value: Inteligência e Precisão")
st.markdown("Extração integral, cronológica e com pré-configuração inteligente.")

# 1. Upload do Arquivo
arquivo_pdf = st.file_uploader("Selecione o Extrato Bancário (PDF)", type="pdf")

if arquivo_pdf:
    linhas_texto = []
    banco_identificado = "Desconhecido"
    
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        for pagina in pdf.pages:
            texto_puro = pagina.extract_text()
            
            # Inteligência: Identifica o banco para sugerir colunas (Lógica similar ao JSON)
            if texto_puro and "SICOOB" in texto_puro.upper():
                banco_identificado = "SICOOB"
            
            # Extração linha a linha para manter a ordem cronológica
            tabela = pagina.extract_table({
                "vertical_strategy": "text",
                "horizontal_strategy": "lines",
                "intersection_y_tolerance": 5,
            })
            
            if tabela:
                for linha in tabela:
                    linha_limpa = [str(c).replace('\n', ' ').strip() if c else "" for c in linha]
                    if any(linha_limpa):
                        linhas_texto.append(linha_limpa)

    if linhas_texto:
        df_b = pd.DataFrame(linhas_texto)

        # ---------------------------------------------------------
        # 1. PRINT DO CABEÇALHO (PRÉVIA REAL)
        # ---------------------------------------------------------
        st.subheader(f"🔍 Verificação: Banco Identificado como {banco_identificado}")
        st.dataframe(df_b.head(50), use_container_width=True)

        # ---------------------------------------------------------
        # 2. CALIBRAÇÃO INTELIGENTE (JSON-Like)
        # ---------------------------------------------------------
        # Se for Sicoob, ele já sugere as colunas que identificamos nos testes
        val_data = 0 if banco_identificado == "SICOOB" else 0
        val_hist = 2 if banco_identificado == "SICOOB" else 1
        val_valor = (len(df_b.columns)-1) if banco_identificado == "SICOOB" else 2

        st.markdown("### ⚙️ Calibração de Colunas")
        col1, col2, col3 = st.columns(3)
        with col1: c_data = st.number_input("Nº coluna DATA", value=val_data)
        with col2: c_desc = st.number_input("Nº coluna HISTÓRICO", value=val_hist)
        with col3: c_valor = st.number_input("Nº coluna VALOR", value=val_valor)

        if st.button("🚀 PROCESSAR EXTRATO COMPLETO"):
            try:
                # Mantém a ordem original das linhas
                df_f = df_b.iloc[:, [c_data, c_desc, c_valor]].copy()
                df_f.columns = ['DATA', 'HISTORICO', 'VALOR_BRUTO']

                # 3. LÓGICA DE INDICATIVO (C/D) E VALOR LIMPO
                def tratar_financeiro(v_bruto):
                    v = str(v_bruto).upper().strip()
                    if not v or v == "NONE": return pd.Series(["", ""])
                    
                    # Identifica sinal de débito
                    indicativo = "D" if "-" in v or "D" in v else "C"
                    # Limpa valor mantendo números e decimais
                    valor_num = re.sub(r'[^\d,.]', '', v)
                    return pd.Series([valor_num, indicativo])

                df_f[['VALOR', 'INDICATIVO']] = df_f['VALOR_BRUTO'].apply(tratar_financeiro)
                
                # Resultado Final (Extração Integral)
                df_final = df_f[['DATA', 'HISTORICO', 'VALOR', 'INDICATIVO']]

                st.success("✅ Extração concluída respeitando a cronologia do documento.")
                st.dataframe(df_final, use_container_width=True)

                csv = df_final.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 Baixar CSV Fair Value", csv, "extrato_fairvalue.csv", "text/csv")

            except Exception as e:
                st.error(f"Erro no processamento: {e}")
