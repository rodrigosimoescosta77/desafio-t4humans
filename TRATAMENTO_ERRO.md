# TRATAMENTO_DE_ERROS

Este documento descreve como o projeto Banco Ágil trata exceções, registra erros e onde os eventos de erro são armazenados.

## 1. Logging centralizado

O projeto possui um logger central configurado em `banco-agil/utils/logging_config.py`.

### Comportamento do logger

- Logs são criados pelo logger nomeado `banco_agil`.
- Todos os módulos importantes do sistema utilizam `setup_logging()` para obter o mesmo logger.
- O logger grava mensagens em arquivo de log e pode disparar alertas externos.

### Destino padrão dos logs

- O arquivo de log padrão é `banco-agil/logs/banco_agil.log`.
- Se o diretório `logs/` não existir, ele é criado automaticamente.
- O arquivo registra mensagens com timestamp, nível, nome do logger e texto do evento.

## 2. Alertas de erros críticos

O sistema suporta alertas de nível `ERROR` ou superior em dois canais opcionais:

### Slack

- Variável de ambiente: `SLACK_WEBHOOK_URL`
- Quando definida, o projeto utiliza `SlackAlertHandler` para enviar notificações de erro ao webhook.
- Apenas logs com nível `ERROR` ou superior são encaminhados ao Slack.

### E-mail (SMTP)

- Variáveis de ambiente:
  - `SMTP_HOST`
  - `SMTP_PORT`
  - `SMTP_FROM`
  - `SMTP_USERNAME` (opcional)
  - `SMTP_PASSWORD` (opcional)
  - `ALERT_EMAIL_RECIPIENTS`
- Se `SMTP_HOST` e `ALERT_EMAIL_RECIPIENTS` estiverem definidos, o sistema cria um handler SMTP.
- Caso as credenciais estejam disponíveis, a conexão SMTP é feita com autenticação.
- O assunto do e-mail é: `[Banco Ágil] Alerta de exceção crítica`.

## 3. Tratamento de erros em `BancoAgilSession`

O arquivo `banco-agil/utils/session.py` concentra a execução do grafo de atendimento e também captura exceções de alto nível.

### Fluxo de erro

- A cada mensagem do usuário, o método `BancoAgilSession.processar_mensagem()` invoca `banco_graph.invoke(state)`.
- Se ocorrer qualquer exceção durante a invocação do grafo:
  - a mensagem problemática é removida do histórico (`self.state["messages"].pop()`).
  - o erro é registrado com `logger.exception(...)` contendo:
    - texto da mensagem
    - agente atual
    - dados parciais do estado do cliente
  - o usuário recebe uma resposta genérica: `Desculpe, ocorreu um erro interno. Por favor, tente novamente.`

## 4. Tratamento de erros nas ferramentas

As funções em `banco-agil/tools/ferramentas.py` implementam tratamento de exceções local para cada ferramenta.

### Principais comportamentos

- Cada ferramenta utiliza `try/except` para capturar falhas de leitura/escrita de arquivo, chamadas HTTP e validação de dados.
- Em caso de erro interno, elas retornam um dicionário com a chave `erro` em vez de lançar exceção.
- Erros de validação esperados (por exemplo, entrada numérica inválida) são registrados como `logger.warning(...)` e retornam mensagens de erro amigáveis.
- Erros inesperados são registrados com `logger.exception(...)`.

### Exemplos de ferramentas com tratamento

- `autenticar_cliente`: falha de I/O ou base inacessível gera log e retorno de erro.
- `consultar_limite_credito`: falha na leitura do CSV gera log e retorno de erro.
- `solicitar_aumento_limite`: erros de arquivo ou cálculos são registrados e retornam erro.
- `calcular_e_atualizar_score`: valida valores, registra warnings para entradas inválidas e exceptions para falhas inesperadas.
- `consultar_cotacao`: falhas de rede/API são registradas e retornam um erro amigável.

## 5. Onde os erros são salvos

### Armazenamento de eventos de erro

- Sim: erros são salvos em `banco-agil/logs/banco_agil.log`.
- Não: não existe um banco de dados de erros separado; o registro persistente é somente o arquivo de log.
- As ferramentas e o gerenciador de sessão não gravam erros em CSV ou outro armazenamento além do log e dos registros normais de negócio.

### Quando não há logs gravados

- Se `banco-agil/utils/logging_config.py` não puder criar o diretório `logs/`, o logger tentará falhar com uma exceção de inicialização no momento da criação do logger.
- Entretanto, o padrão do projeto é criar o diretório automaticamente, garantindo que os logs sejam persistidos.

## 6. Recomendações de uso

- Verifique `logs/banco_agil.log` para investigar exceções internas e falhas inesperadas.
- Use `SLACK_WEBHOOK_URL` para receber alertas imediatos de erros críticos em produção.
- Use SMTP apenas em ambientes controlados para evitar envio desnecessário de e-mail.
- Em caso de erro recorrente, consulte primeiro o stack trace no arquivo de log.
