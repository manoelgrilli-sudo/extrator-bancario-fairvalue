# ... (parte anterior do código igual)

    st.subheader("📋 Passo 2: Calibração de Colunas")
    
    # Adicionando uma caixa de ajuda focada na sua ideia
    st.info("💡 **Dica do Especialista:** Olhe para os títulos na tabela abaixo. O número acima de cada coluna é o que você deve digitar nos campos de calibração.")

    # Apresenta a prévia com mais destaque
    st.dataframe(df_b.head(15), use_container_width=True)

    st.markdown("---")
    st.write("🎯 **Defina as colunas baseadas na prévia acima:**")
    
    col1, col2, col3 = st.columns(3)
    with col1: 
        c_data = st.number_input("Coluna de DATA", min_value=0, value=0, help="Geralmente a primeira coluna (0)")
    with col2: 
        c_desc = st.number_input("Coluna de HISTÓRICO", min_value=0, value=2, help="Procure onde estão os nomes dos clientes")
    with col3: 
        c_valor = st.number_input("Coluna de VALOR", min_value=0, value=3, help="Coluna com os valores e sinais C/D")

    # ... (restante do código para gerar a movimentação líquida)
