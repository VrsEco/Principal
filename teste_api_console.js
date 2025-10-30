// TESTE DAS APIs - Cole este código no Console do navegador (F12)

console.log('TESTANDO APIs...');
console.log('');

// API 1: Produtos completos
fetch('/pev/api/implantacao/6/products')
  .then(r => r.json())
  .then(data => {
    console.log('===============================================');
    console.log('API /products');
    console.log('===============================================');
    console.log('Success:', data.success);
    console.log('Produtos encontrados:', data.products?.length || 0);
    console.log('Totals completo:', data.totals);
    console.log('Faturamento:', data.totals?.faturamento);
    console.log('Custos variaveis:', data.totals?.custos_variaveis);
    console.log('Margem:', data.totals?.margem_contribuicao);
    console.log('');
  })
  .catch(err => console.error('ERRO /products:', err));

// API 2: Apenas totais
fetch('/pev/api/implantacao/6/products/totals')
  .then(r => r.json())
  .then(data => {
    console.log('===============================================');
    console.log('API /products/totals');
    console.log('===============================================');
    console.log('Success:', data.success);
    console.log('Totals completo:', data.totals);
    console.log('Faturamento:', data.totals?.faturamento);
    console.log('Custos variaveis:', data.totals?.custos_variaveis);
    console.log('Margem:', data.totals?.margem_contribuicao);
    console.log('');
  })
  .catch(err => console.error('ERRO /products/totals:', err));

// API 3: Custos fixos
fetch('/pev/api/implantacao/6/structures/fixed-costs-summary')
  .then(r => r.json())
  .then(data => {
    console.log('===============================================');
    console.log('API /structures/fixed-costs-summary');
    console.log('===============================================');
    console.log('Success:', data.success);
    console.log('Data completo:', data.data);
    console.log('Custos fixos:', data.data?.custos_fixos_mensal);
    console.log('Despesas fixas:', data.data?.despesas_fixas_mensal);
    console.log('');
  })
  .catch(err => console.error('ERRO /structures:', err));

console.log('Aguarde 2 segundos para ver os resultados...');

