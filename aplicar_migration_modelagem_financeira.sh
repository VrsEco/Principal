#!/bin/bash

echo "============================================"
echo "  MIGRATION: Modelagem Financeira"
echo "  Adicionando campo 'notes' em plan_finance_metrics"
echo "============================================"
echo ""

# Executar migration dentro do container PostgreSQL
docker exec -i gestaoversos_db_prod psql -U postgres -d bd_app_versus < migrations/add_notes_to_finance_metrics.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "✅ MIGRATION APLICADA COM SUCESSO!"
    echo "============================================"
    echo ""
    echo "Campo 'notes' adicionado à tabela plan_finance_metrics"
    echo ""
    echo "Agora você pode testar a página:"
    echo "  http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=45"
    echo ""
    echo "(Substitua plan_id=45 por um ID válido!)"
    echo ""
else
    echo ""
    echo "❌ ERRO ao aplicar migration!"
    echo ""
    echo "Verifique se o container está rodando:"
    echo "  docker ps"
    echo ""
    echo "Se necessário, inicie os containers:"
    echo "  docker-compose up -d"
    echo ""
fi


