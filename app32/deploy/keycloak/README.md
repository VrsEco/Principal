# Keycloak — artefatos de implantação APP32

Estes arquivos são templates versionados. Keycloak é um serviço independente
do Flask/App32, com PostgreSQL, runtime, logs e segredos próprios fora deste
repositório.

- `keycloak-local.env.template`: variáveis mínimas para homologação local sem
  Docker, usando PostgreSQL local dedicado.
- `keycloak.service.template`: unidade systemd de referência para ambiente
  posterior. Ela exige `keycloak.env` externo ao Git e não é instrução de
  deploy automático.
- `realm-template.json`: contrato declarativo de realm/scopes e cliente USER
  PKCE local. Não contém segredo e independe de Docker; client confidencial,
  senha e usuários são criados fora do Git.
- `configr/`: contrato de implantação Docker do Keycloak no Configr. A pasta
  contém somente imagem/versionamento, PostgreSQL dedicado e topologia de
  rede; o arquivo `keycloak.env` fica em diretório externo e protegido.

Não incluir neste diretório: binários Keycloak, dumps, bancos, senhas,
certificados, tokens, realm exportado com credenciais ou dados de usuários.

O procedimento canônico está em
`app32/docs/runbooks/runbook_keycloak_local_postgres_sem_docker_v1.md` para
homologação local e em
`app32/docs/runbooks/runbook_keycloak_configr_docker_v1.md` para produção
controlada no Configr.
