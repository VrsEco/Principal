# Runtime Checklist

Use este checklist quando houver suspeita de divergência entre código publicado e comportamento real.

## 1. Código publicado
- confirmar arquivo local x remoto
- conferir hash/trecho crítico
- confirmar template e JS servidos no fluxo afetado

## 2. Boot limpo
Validar que a aplicação sobe limpa com o ambiente alvo.
Exemplos de evidência:
- `create_app('production')` concluído com sucesso
- imports críticos carregados
- recursos/blueprints registrados

## 3. Restart real
Não aceitar apenas `touch restart.txt` como prova suficiente.
Validar:
- PIDs novos do uWSGI/vassal
- ausência de worker antigo misturado
- aplicação respondendo após restart

## 4. Pós-deploy
Executar smoke mínimo:
- login
- endpoint crítico do fluxo alterado
- um caso real ou reprodução fiel

## 5. Sinais de alerta
- request entra no log e não há `Response`
- comportamento muda sem alteração de código
- endpoint funciona por teste interno e falha no navegador
- import quebrado no cold start
- deploy completo reverte hotfix não commitado
