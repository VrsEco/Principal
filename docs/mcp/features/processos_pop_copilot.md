# Guia da Feature: POP Copilot com Vídeo Curto por Passo

## Metadados
- `feature_id`: `processos_pop_copilot`
- `dominio`: `processes`
- `surfaces_permitidas`: `user`, `admin`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Permitir que um passo de POP tenha:
- print/imagem;
- texto descritivo;
- vídeo curto opcional como evidência de execução correta;
- narração/contexto do operador;
- leitura MCP do contexto multimídia para orientar a próxima ação.

## Quando usar
- documentar como executar um passo específico
- registrar navegação curta em sistema
- capturar um microprocedimento operacional
- preparar um POP com menos trabalho manual

## Quando não usar
- gravar o POP inteiro em um único vídeo longo
- usar vídeo sem revisão humana do print e da descrição
- tratar vídeo como substituto da descrição textual final

## Entradas esperadas
### Obrigatórias
- `company_id`
- `step_id` ou contexto do passo no detalhe do processo

### Opcionais
- `video_mp4_ou_webm`
- `descricao_do_passo`
- `print_extraido_do_video`
- `narracao_do_operador`

## Saídas esperadas
- `video_vinculado_ao_passo`
- `duracao_do_video`
- `print_do_frame_atual`
- `contexto_mcp_do_passo`
- `acoes_recomendadas`
- `rascunho_inicial_da_descricao`

## Como orientar o usuário
- pedir um vídeo curto de até 2 minutos
- orientar um vídeo por passo, não por atividade inteira
- depois do upload, pedir para escolher o frame mais útil como print
- usar a narração do operador para melhorar o rascunho automático
- manter a revisão humana do texto e do resultado esperado

## Validações e restrições
- `company_id` obrigatório
- sem cruzamento entre tenants
- formatos aceitos no MVP: `MP4` e `WebM`
- duração máxima: `120 segundos`
- revisão humana continua obrigatória antes da publicação do POP

## O que nunca expor
- mídia de outro tenant
- arquivos sem referência operacional ao passo
- decisões automáticas de publicação sem revisão
