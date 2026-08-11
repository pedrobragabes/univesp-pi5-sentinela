# Revisão de código

Revisão realizada antes da publicação da fundação técnica do Sentinela.

## Escopo

- leitura, validação e filtragem no firmware;
- relógio, reconexão e transmissão;
- contrato, autenticação e idempotência;
- transações e ciclo de vida do SQLite;
- simulador, painel, segurança e responsividade;
- testes Python, testes C++ e build ESP32.

## Achados corrigidos

### R1 — conexões SQLite permaneciam abertas no Windows

**Severidade:** alta.

O context manager nativo do `sqlite3` confirma ou desfaz a transação, mas não fecha automaticamente a conexão. Os seis testes funcionavam e falhavam somente na remoção dos bancos temporários. Foi criado um context manager explícito que faz commit/rollback e sempre fecha a conexão.

### R2 — relógio não era sincronizado após falha inicial de Wi-Fi

**Severidade:** alta.

O NTP era configurado apenas no `setup`. Se a rede estivesse indisponível nesse momento, reconexões posteriores nunca iniciariam a sincronização e nenhuma mensagem teria timestamp válido. A verificação passou para a rotina de conexão e ocorre sempre que o relógio ainda é inválido.

### R3 — possível truncamento silencioso da mensagem

**Severidade:** média.

O retorno de `snprintf` não era inspecionado. O firmware agora cancela a transmissão quando a serialização não cabe no buffer.

### R4 — simulador reutilizava a mesma inicialização

**Severidade:** média.

Ao reiniciar o simulador, sequências anteriores eram tratadas corretamente como duplicadas, mas isso confundia novas demonstrações. Cada execução agora cria um `boot_id` aleatório; os testes continuam podendo injetar um valor fixo.

### R5 — timestamp extremo chegava à biblioteca do sistema

**Severidade:** baixa.

Foi adicionada uma faixa absoluta antes da conversão de época, além da janela móvel de 24 horas.

### R6 — alfa do filtro não tinha limite

**Severidade:** baixa.

Valores fora de 0 a 1 poderiam amplificar o sinal. O construtor agora restringe o coeficiente à faixa válida e há teste C++ específico.

## Evidências verificadas

- 6 testes Python aprovados;
- dependências Python consistentes;
- firmware compilado para ESP32 Dev Module;
- uso do build: 46.852 bytes de RAM e 919.313 bytes da partição de aplicação;
- 8 mensagens do simulador aceitas de ponta a ponta;
- painel verificado em 1280 px e 390 px, sem rolagem horizontal da página;
- tabela móvel isolada em contêiner rolável;
- cabeçalhos CSP, `nosniff`, negação de frames e política sem referenciador.

## Limites e riscos aceitos

- teste C++ nativo não executado neste Windows por ausência de `gcc/g++`; ficará obrigatório na CI Linux;
- comunicação HTTP é somente para rede local de demonstração;
- chave compartilhada única é insuficiente para frota ou produção;
- não há fila persistente no ESP32: amostras não confirmadas são tentadas novamente apenas no próximo ciclo;
- DHT22 e ESP32 não foram conectados, calibrados ou ensaiados fisicamente;
- o servidor Flask de desenvolvimento não é configuração de produção.

## Parecer

O software e o firmware estão adequados para publicação como fundação técnica compilável e simulável. O PI V somente poderá ser apresentado como protótipo físico validado após montagem, ensaios, registro de evidências e participação real do parceiro.
