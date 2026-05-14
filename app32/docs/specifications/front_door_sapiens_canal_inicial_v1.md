# Front Door, Papel do Sapiens e Canal Inicial de Uso — Versus Gestão Corporativa

## Status
Versão inicial v1 produzida no contexto do card `AA.J.15.3`.

## Objetivo
Definir a experiência de entrada oficial da Versus Gestão Corporativa para o modelo híbrido assistido, incluindo:
- papel do `Sapiens`
- papel dos demais contatos/squads
- canal inicial de uso
- regra de despacho entre humano e squads

---

## 1. Achados do estado atual
A base atual já aponta fortemente para o `Sapiens` como hub de entrada.

### Evidências no código
- há rota dedicada `/sapiens`
- existem wrappers de superfícies que redirecionam para o Sapiens
- existem descrições explícitas de “Wrapper Sapiens” nas rotas de agentes
- existem fluxos omnichannel com `contact = sapiens`
- existem artefatos de onboarding e surfaces externas ligados ao ecossistema Sapiens

### Leitura
O sistema já vem migrando, de forma prática, para uma ideia de **hub único de entrada** em torno do Sapiens.

---

## 2. Decisão arquitetural recomendada
### 2.1 Papel oficial do Sapiens
O `Sapiens` deve ser a **camada oficial de front door** da Versus Gestão Corporativa.

Ele não deve ser entendido apenas como “mais um agente”.

Ele deve operar como:
- entrada universal da experiência
- tradutor de intenção
- roteador de fluxo
- camada inicial de utilização assistida
- facilitador de descoberta de capabilities do APP32
- ponte entre usuário, APP32, Squad Cliente e Squad Versus

### 2.2 O que o Sapiens não deve ser
O `Sapiens` não deve se tornar:
- especialista profundo único de todos os domínios
- substituto de todos os squads
- atalho para contornar governança de surface ou capability
- executor irrestrito sem despacho correto

---

## 3. Regra de experiência de entrada
### 3.1 Entrada preferencial
A entrada preferencial do usuário deve ocorrer pelo `Sapiens`.

### 3.2 Escolha explícita de squads
O usuário final não precisa começar escolhendo manualmente entre `Squad Versus` e `Squad Cliente`.

A experiência ideal é:
1. usuário entra pelo Sapiens
2. Sapiens entende intenção, maturidade e contexto
3. Sapiens orienta, responde diretamente quando cabível ou despacha para o fluxo/squad correto

### 3.3 Contatos especializados
Contatos como `engineering` ou `factory` podem existir, mas como trilhas especializadas e não como front door padrão do uso comum.

---

## 4. Papel do Sapiens no modelo híbrido assistido
No modelo de adoção recomendado (`Modelo B — híbrido assistido`), o `Sapiens` deve assumir quatro funções simultâneas:

### 4.1 Recepção
Receber o usuário com baixo atrito, principalmente nos primeiros usos.

### 4.2 Tradução
Converter pedidos vagos em caminhos operacionais mais claros.

### 4.3 Despacho
Decidir quando o pedido:
- é resolvido ali mesmo
- segue para o `Squad Cliente`
- segue para o `Squad Versus`
- exige humano
- exige surface/fluxo especial

### 4.4 Educação de uso
Ajudar o usuário a aprender:
- como pedir melhor
- como usar o APP32
- como aproveitar os squads
- como ganhar autonomia progressivamente

---

## 5. Canal inicial de uso recomendado
### 5.1 Recomendação principal
O canal inicial de uso deve ser:

- **APP32 com interface guiada do Sapiens**

### Justificativa
Esse canal:
- reduz barreira de adoção
- evita exigir CLI no início para usuários comuns
- facilita utilização assistida
- mantém o APP32 como espaço operacional comum
- permite convergir depois para canais adicionais

### 5.2 Canais secundários permitidos
Podem coexistir como canais complementares:
- WhatsApp
- Telegram
- outros canais conversacionais existentes
- runtimes externos da Versus e do cliente, quando aplicável

### 5.3 Observação importante
Os runtimes externos dos squads continuam sendo parte da arquitetura-alvo, mas **não devem ser a exigência inicial para todo usuário humano**.

---

## 6. Papel dos runtimes externos no front door
### 6.1 Consultor da Versus
Pode operar diretamente o `Squad Versus` em runtime externo autorizado.

### 6.2 Cliente maduro
Pode, em estágio posterior, operar o `Squad Cliente` em runtime externo próprio.

### 6.3 Usuário comum no início
Deve preferencialmente entrar pelo APP32/Sapiens, com experiência assistida.

---

## 7. Fluxo recomendado de despacho inicial
### 7.1 Pedido simples ou de orientação
- o `Sapiens` responde diretamente

### 7.2 Pedido operacional do dia a dia
- o `Sapiens` aciona o fluxo do `Squad Cliente` ou conduz o usuário até a capability correta

### 7.3 Pedido consultivo, estrutural, crítico ou de governança
- o `Sapiens` encaminha para a lógica do `Squad Versus`

### 7.4 Pedido técnico/fábrica/engenharia
- o `Sapiens` ou a interface especializada encaminha para `engineering` ou `factory`

## 4.1 Convenção de nome nas instalações de CLI
Quando houver mais de uma instalação no mesmo cliente/CLI, o front door `Sapiens` deve aparecer separado por contexto:

- `Sapiens Cliente`
- `Sapiens Consultor`
- `Sapiens Engenharia`

Regra:
- `Sapiens` continua como marca e camada de entrada
- os nomes acima são a apresentação visível no cliente/CLI
- a arquitetura interna continua usando `Squad Cliente`, `Squad Versus` e `engineering`

---

## 8. Relação com utilização assistida
O `Sapiens` é a principal camada operacional do modo de utilização assistida.

Isso significa que ele deve:
- orientar a formulação da demanda
- sugerir próximos passos
- revelar possibilidades do APP32
- adaptar a profundidade da ajuda ao nível de maturidade do usuário

---

## 9. Gaps ainda existentes
1. falta política explícita de despacho entre Sapiens, Squad Cliente e Squad Versus
2. falta costura formal entre front door e identidade por ator
3. falta amarração operacional com objetos colaborativos mínimos
4. falta definição prática do primeiro fluxo MVP assistido já conectado a esse front door

---

## 10. Decisão final recomendada do passo
### Decisão
- `Sapiens` = front door oficial
- `APP32/Sapiens` = canal inicial de uso recomendado
- `Modelo B híbrido assistido` = estratégia de entrada
- `Squad Cliente` e `Squad Versus` = camadas especializadas por trás do front door
- `engineering/factory` = trilhas especializadas, não canal primário de usuário comum

---

## 11. Impacto no backlog seguinte
Esta definição habilita diretamente:
- modelagem dos objetos colaborativos mínimos
- recorte do primeiro fluxo MVP operacional assistido
- desenho do despacho entre Sapiens, squads e humano

---

## 12. Veredito final do Passo 3
A direção arquitetural mais coerente é usar o `Sapiens` como hub oficial de entrada da Versus Gestão Corporativa.

Isso preserva:
- baixa fricção de adoção
- coerência de experiência
- governança gradual
- utilização assistida
- possibilidade de evolução posterior para operação distribuída mais madura
