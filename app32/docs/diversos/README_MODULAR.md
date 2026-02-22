# PEVAPP22 - Sistema Modular com Troca Fácil de Banco de Dados

## 🎯 Visão Geral

O PEVAPP22 agora possui uma arquitetura modular que permite trocar facilmente entre diferentes bancos de dados sem modificar o código da aplicação. O sistema implementa uma camada de abstração de banco de dados que suporta SQLite e PostgreSQL.

## 🏗️ Arquitetura

### Estrutura de Arquivos

```
pevapp22/
├── database/                 # Camada de abstração de banco de dados
│   ├── __init__.py          # Factory para criar instâncias de banco
│   ├── base.py              # Interface abstrata (contrato)
│   ├── sqlite_db.py         # Implementação SQLite
│   └── postgresql_db.py     # Implementação PostgreSQL
├── config_database.py       # Configuração e gerenciamento de banco
├── app_pev.py               # Aplicação principal PEV
├── test_database_switching.py # Teste de troca de banco
└── README_MODULAR.md        # Esta documentação
```

### Camada de Abstração

A camada de abstração define um contrato (`DatabaseInterface`) que todas as implementações de banco devem seguir:

```python
class DatabaseInterface(ABC):
    @abstractmethod
    def get_companies(self) -> List[Dict[str, Any]]:
        """Get all companies"""
        pass
    
    @abstractmethod
    def get_plan_with_company(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Get plan with company information"""
        pass
    
    # ... outros métodos
```

## 🚀 Como Usar

### 1. Executar a Aplicação

```bash
# Usar SQLite (padrão)
python app_pev.py

# Ou definir variável de ambiente
export DB_TYPE=sqlite
python app_pev.py
```

### 2. Trocar para PostgreSQL

```bash
# Definir variáveis de ambiente
export DB_TYPE=postgresql
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=pevapp22
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=password

python app_pev.py
```

### 3. Trocar Programaticamente

```python
from config_database import switch_database

# Trocar para SQLite
db = switch_database('sqlite', db_path='meu_app.db')

# Trocar para PostgreSQL
db = switch_database('postgresql', 
                    host='localhost', 
                    port=5432, 
                    database='meu_app', 
                    user='postgres', 
                    password='password')
```

## 📊 Funcionalidades por Página

### Dashboard
- ✅ Lista empresas e planos do banco de dados
- ✅ Navegação entre empresas e planos
- ✅ Estatísticas e timeline

### Dados da Organização
- ✅ Visualizar dados da empresa
- ✅ Editar informações corporativas
- ✅ Salvar alterações no banco

### Participantes
- ✅ Listar participantes do plano
- ✅ Adicionar novos participantes
- ✅ Remover participantes

### Direcionadores
- ✅ Visualizar direcionadores estratégicos
- ✅ Adicionar novos direcionadores
- ✅ Gerenciar status e prioridades

### OKRs
- ✅ OKRs Globais: Criar e gerenciar
- ✅ OKRs de Área: Organizar por área
- ✅ Status e acompanhamento

### Projetos
- ✅ Listar projetos do plano
- ✅ Adicionar novos projetos
- ✅ Gerenciar status e datas

### Relatórios
- ✅ Visualizar dados consolidados
- ✅ Gerar relatórios (PDF em desenvolvimento)
- ✅ Exportar informações

## 🔧 Operações CRUD

### Create (Criar)
```python
# Adicionar participante
db.add_participant(plan_id, {
    'name': 'João Silva',
    'role': 'Gerente',
    'email': 'joao@empresa.com',
    'phone': '(11) 99999-0001'
})

# Adicionar direcionador
db.add_driver(plan_id, {
    'title': 'Digitalização',
    'description': 'Implementar sistemas digitais',
    'status': 'draft',
    'priority': 'high',
    'owner': 'João Silva'
})
```

### Read (Ler)
```python
# Obter empresas
companies = db.get_companies()

# Obter plano com empresa
plan_data = db.get_plan_with_company(plan_id)

# Obter participantes
participants = db.get_participants(plan_id)
```

### Update (Atualizar)
```python
# Atualizar dados da empresa
db.update_company_data(plan_id, {
    'trade_name': 'Nova Empresa',
    'mission': 'Nova missão',
    'vision': 'Nova visão'
})
```

### Delete (Deletar)
```python
# Remover participante
db.delete_participant(participant_id)
```

## 🗄️ Suporte a Bancos de Dados

### SQLite
- ✅ **Desenvolvimento**: Ideal para desenvolvimento local
- ✅ **Simplicidade**: Sem configuração de servidor
- ✅ **Portabilidade**: Arquivo único
- ✅ **Performance**: Rápido para pequenos volumes

### PostgreSQL
- ✅ **Produção**: Ideal para ambientes de produção
- ✅ **Escalabilidade**: Suporta grandes volumes
- ✅ **Recursos**: Recursos avançados de banco
- ✅ **Concorrência**: Múltiplos usuários simultâneos

## 🔄 Troca de Banco de Dados

### Método 1: Variáveis de Ambiente

```bash
# SQLite
export DB_TYPE=sqlite
export SQLITE_DB_PATH=meu_app.db

# PostgreSQL
export DB_TYPE=postgresql
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=meu_app
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=password
```

### Método 2: Código Python

```python
from config_database import switch_database

# Trocar para SQLite
db = switch_database('sqlite', db_path='meu_app.db')

# Trocar para PostgreSQL
db = switch_database('postgresql', 
                    host='localhost', 
                    port=5432, 
                    database='meu_app', 
                    user='postgres', 
                    password='password')
```

### Método 3: Arquivo .env

```env
# .env
DB_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pevapp22
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
```

## 🧪 Testes

### Executar Testes

```bash
# Testar troca de banco de dados
python test_database_switching.py

# Testar aplicação
python app_pev.py
```

### Verificar Funcionamento

1. **Acesse**: http://127.0.0.1:5002
2. **Navegue**: Entre as páginas do sistema
3. **Teste CRUD**: Adicione, edite e remova dados
4. **Verifique persistência**: Recarregue a página

## 🎯 Benefícios da Arquitetura Modular

### ✅ Facilidade de Troca
- Mude o banco de dados com uma linha de código
- Sem modificações na lógica da aplicação
- Suporte a múltiplos backends

### ✅ Interface Consistente
- Mesmos métodos funcionam para todos os bancos
- Tratamento unificado de erros
- Estruturas de dados consistentes

### ✅ Flexibilidade de Desenvolvimento
- Use SQLite para desenvolvimento
- Troque para PostgreSQL em produção
- Teste fácil com diferentes bancos

### ✅ Preparado para o Futuro
- Fácil adicionar novos tipos de banco
- Estrutura de código mantível
- Separação clara de responsabilidades

### ✅ Gerenciamento de Configuração
- Configuração baseada em ambiente
- Deploy fácil entre ambientes
- Gerenciamento seguro de credenciais

## 🚀 Próximos Passos

1. **Teste todas as funcionalidades** navegando pelo sistema
2. **Adicione dados reais** usando os formulários
3. **Teste a persistência** recarregando as páginas
4. **Experimente trocar bancos** usando os métodos documentados
5. **Configure para produção** com PostgreSQL

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs do servidor
2. Execute os testes de banco de dados
3. Consulte esta documentação
4. Verifique as configurações de ambiente

---

**🎉 O sistema modular está funcionando perfeitamente! Agora você pode trocar facilmente entre diferentes bancos de dados conforme suas necessidades.**
