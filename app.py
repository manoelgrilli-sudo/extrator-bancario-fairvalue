import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="Fair Value - Extrator de Precisão", layout="wide")

st.title("🏦 Extrator Fair Value: Precisão Total")
st.markdown("Este modelo lê o texto linha por linha, garantindo que nomes de clientes e valores não sejam ignorados.")

arquivo_pdf = st.file_uploader("Selecione o Extrato Bancário (PDF)", type="pdf")

if arquivo_pdf:
    linhas_texto = []
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        for pagina in pdf.pages:
            # Extração por linha de texto (contorna o erro de tabelas invisíveis)
            text = pagina.extract_text()
            if text:
                for linha in text.split('\n'):
                    # Divide a linha em 'pedaços' baseado em espaços duplos
                    partes = re.split(r'\s{2,}', linha.strip())
                    if len(partes) > 1:
                        linhas_texto.append(partes)

    if linhas_texto:
        # Criamos o DataFrame com o máximo de colunas encontradas
        df_b = pd.DataFrame(linhas_texto)

        st.subheader("🔍 1. Print do Texto Extraído")
        st.info("O sistema agora lê cada linha de texto. Identifique abaixo as colunas desejadas.")
        st.dataframe(df_b.head(100), use_container_width=True)

        st.markdown("### ⚙️ 2. Calibração")
        col1, col2, col3 = st.columns(3)
        with col1: c_data = st.number_input("Nº coluna de DATA", min_value=0, value=0)
        with col2: c_desc = st.number_input("Nº coluna de HISTÓRICO", min_value=0, value=1)
        with col3: c_valor = st.number_input("Nº coluna de VALOR", min_value=0, value=len(df_b.columns)-1)

        if st.button("🚀 PROCESSAR TUDO"):
            try:
                # Extração Integral
                df_f = df_b.iloc[:, [c_data, c_desc, c_valor]].copy()
                df_f.columns = ['DATA', 'HISTORICO', 'VALOR_BRUTO']
                
                def tratar_financeiro(v_bruto):
                    texto = str(v_bruto).upper()
                    if not texto.strip() or texto == "NONE": return pd.Series(["", ""])
                    
                    # Identifica D se houver sinal de menos (-) ou a letra D
                    indicativo = "D" if "-" in texto or "D" in texto else "C"
                    # Limpa valor
                    valor_num = re.sub(r'[^\d,.]', '', texto)
                    return pd.Series([valor_num, indicativo])

                df_f[['VALOR', 'INDICATIVO']] = df_f['VALOR_BRUTO'].apply(tratar_financeiro)
                df_final = df_f[['DATA', 'HISTORICO', 'VALOR', 'INDICATIVO']].reset_index(drop=True)

                st.success("✅ Extração concluída!")
                st.dataframe(df_final, use_container_width=True)

                csv = df_final.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 Baixar CSV Total", csv, "extrato_total_fairvalue.csv", "text/csv")

            except Exception as e:
                st.error(f"Erro ao processar: {e}")
