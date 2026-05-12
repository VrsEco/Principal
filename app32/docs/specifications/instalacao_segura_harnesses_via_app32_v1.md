# Instalação Segura dos Harnesses via APP32 v1

## Objetivo
Definir o fluxo oficial de instalação dos harnesses dos squads sem embutir segredos no pacote, preservando:
- rotação de token
- revogação simples
- menor exposição do modelo Versus
- experiência prática para cliente e consultor

---

## 1. Decisão principal
O modelo oficial deve ser:

## **APP32 gera contexto + usuário informa token na hora**

Ou seja:
1. o usuário entra no APP32
2. gera o token MCP pessoal
3. o APP32 mostra o comando de instalação do runtime
4. o instalador pede o token de forma segura
5. o instalador grava a configuração local e executa smoke básico

---

## 2. O que não fazer
Não é recomendado:
- embutir token dentro do pacote versionado
- colocar token em arquivo commitado
- passar token em texto puro na linha de comando
- depender de segredo hardcoded no instalador

Motivos:
- risco de vazamento
- histórico de shell
- print/log acidental
- rotação mais difícil

---

## 3. Fluxo recomendado

### 3.1 No APP32
O usuário deve poder:
- gerar token MCP pessoal
- escolher o runtime alvo
  - Codex
  - Claude
  - Antigravity
- copiar o comando de instalação apropriado

### 3.2 No terminal do usuário
O usuário executa o comando de instalação.

O instalador deve:
1. pedir o e-mail
2. pedir o token com entrada segura
3. montar a configuração MCP local
4. copiar ou apontar o harness correto
5. validar `healthz` e configuração mínima
6. orientar o próximo passo

---

## 4. Modelo de comando recomendado

### Comando com contexto, sem segredo
Exemplo conceitual:

```powershell
$env:GV_PROFILE='engineering'; `
$env:GV_SURFACE='ops'; `
$env:GV_COMPANY_ID='10'; `
irm https://<repositorio-ou-endpoint>/install-codex-laboratorio.ps1 | iex
```

O token **não** deve vir embutido no comando.

---

## 5. Modelo do instalador

### Entrada obrigatória
- e-mail do usuário
- token MCP gerado no APP32

### Entrada contextual
- `company_id`
- `profile`
- `surface`
- `base_url`

### Saída esperada
- `.mcp.json` local configurado
- backup automático do arquivo anterior
- referência do harness a ser usado
- smoke básico concluído

---

## 6. Papel do APP32
O APP32 continua sendo o emissor canônico de:
- token
- profile
- surface
- company_id
- URL base do MCP
- instrução de instalação

O APP32 **não** deve depender de pacote com segredo embutido.

---

## 7. Papel do repositório de harnesses
O repositório separado de harnesses deve conter:
- harnesses por runtime
- templates de configuração
- scripts de instalação
- smoke scripts
- manifest/versionamento

Não deve conter:
- tokens reais
- segredos
- credenciais persistentes de cliente

---

## 8. Aplicação ao laboratório atual

### Codex / Engenharia
- profile: `engineering`
- surface: `ops`
- `company_id`: `10`
- instalador de referência:
  - `C:\GestaoVersus\app32\app32\scripts\installers\install-codex-laboratorio.ps1`

### Claude / Squad Cliente
- profile: `squad_cliente`
- surface: `user`
- `company_id`: `10`
- instalador de referência:
  - `C:\GestaoVersus\app32\app32\scripts\installers\install-claude-laboratorio.ps1`

### Antigravity / Squad Versus
- profile: `squad_versus`
- surface: `admin`
- `company_id`: `10`

---

## 9. Veredito
O modelo mais seguro, prático e elegante para a Versus é:

### **instalador automatizado + token informado no momento da instalação**

Isso mantém boa UX sem sacrificar governança nem segurança operacional.
