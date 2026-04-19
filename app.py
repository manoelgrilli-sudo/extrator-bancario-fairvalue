import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="Fair Value - Extrator Oficial", layout="wide")

st.title("🏦 Extrator Fair Value: Validação e Padronização")

arquivo_pdf = st.file_uploader("Selecione o Extrato Bancário (PDF)", type="pdf")

if arquivo_pdf:
    dados_brutos = []
    with pdfplumber.open(io.BytesIO(arquivo_pdf.read())) as pdf:
        for pagina in pdf.pages:
            tabelas = pagina.extract_tables()
            for tabela in tabelas:
                for linha in tabela:
                    # Converte cada célula para texto e remove espaços extras
                    # Se for None, vira uma string vazia para evitar erro de 'float'
                    linha_limpa = [str(c).strip() if c is not None else "" for c in linha]
                    if any(linha_limpa):
                        dados_brutos.append(linha_limpa)

    if dados_brutos:
        df_b = pd.DataFrame(dados_brutos)

        # 1. APRESENTAR A PRÉVIA (O "PRINT" DO EXTRATO)
        st.subheader("🔍 Verificação do Extrato")
        st.info("Abaixo está o 'print' das colunas encontradas. Identifique os números para configurar o extrator.")
        st.dataframe(df_b.head(50), use_container_width=True)

        st.markdown("### ⚙️ Calibração de Colunas")
        col1, col2, col3 = st.columns(3)
        with col1: c_data = st.number_input("Nº da coluna de DATA", min_value=0, value=0)
        with col2: c_desc = st.number_input("Nº da coluna de HISTÓRICO", min_value=0, value=2)
        with col3: c_valor = st.number_input("Nº da coluna de VALOR", min_value=0, value=3)

        if st.button("🚀 VALIDAR E GERAR MOVIMENTAÇÃO LÍQUIDA"):
            try:
                # Seleciona as colunas definidas pelo operador
                df_f = df_b.iloc[:, [c_data, c_desc, c_valor]].copy()
                df_f.columns = ['DATA', 'HISTORICO', 'VALOR_BRUTO']

                # 2. EXCLUIR SALDOS E CABEÇALHOS
                # Criamos uma lista de termos que indicam saldos ou lixo
                termos_ignorar = ["SALDO", "RESUMO", "DATA", "HISTÓRICO", "VALOR", "DOCUMENTO", "EXTRATO"]
                
                # Filtramos o DataFrame
                mask = df_f['HISTORICO'].str.upper().apply(lambda x: any(t in x for t in termos_ignorar))
                df_f = df_f[~mask]
                
                # Remove linhas onde a data é inválida ou vazia
                df_f = df_f[df_f['DATA'].str.strip() != ""]
                df_f = df_f[df_f['DATA'] != "None"]

                # 3. CRIAR COLUNA INDICATIVO (D/C) E LIMPAR VALOR
                def processar_financas(valor_original):
                    texto = str(valor_original).upper()
                    # Identifica se é Débito (tem sinal de - ou letra D)
                    indicativo = "D" if "-" in texto or "D" in texto else "C"
                    # Limpa o valor para deixar apenas números e separadores
                    valor_num = re.sub(r'[^\d,.]', '', texto)
                    return pd.Series([valor_num, indicativo])

                df_f[['VALOR', 'INDICATIVO']] = df_f['VALOR_BRUTO'].apply(processar_financas)

                # Limpeza final: remove linhas onde o valor ficou vazio
                df_f = df_f[df_f['VALOR'] != ""]

                # Exibição do Resultado
                df_final = df_f[['DATA', 'HISTORICO', 'VALOR', 'INDICATIVO']].reset_index(drop=True)

                st.success(f"✅ Sucesso! {len(df_final)} movimentações líquidas processadas.")
                st.dataframe(df_final, use_container_width=True)

                # Exportação
                csv = df_final.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 Baixar CSV Padronizado", csv, "extrato_padronizado_fairvalue.csv", "text/csv")

            except Exception as e:
                st.error(f"Erro na validação: {e}")
    else:
        st.error("O sistema não encontrou tabelas neste PDF.")
