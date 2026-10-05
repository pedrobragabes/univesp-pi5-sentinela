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

## Evidências da fundação anterior

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
- não há fila persistente no ESP32: a leitura pendente é preservada em RAM e a aquisição pausa até confirmação; reinicialização perde essa leitura;
- DHT22 e ESP32 não foram conectados, calibrados ou ensaiados fisicamente;
- o servidor Flask de desenvolvimento não é configuração de produção.

## Revisão de retransmissão — 5 de outubro de 2026

### R7 — perda de resposta provocava nova leitura com a mesma sequência

O firmware adquiria novos valores e timestamp antes de confirmar a sequência anterior. O receptor aceitava a colisão como duplicata. Agora há um slot imutável em RAM; o próximo ciclo repete seu corpo e a aquisição/filtro só avançam após um recibo correlacionado.

### R8 — qualquer violação de integridade era confirmada como duplicata

O receptor agora reserva uma transação, compara a leitura existente e devolve 409 para qualquer diferença normalizada. Foram reproduzidas colisões em seis campos e duas entregas concorrentes; somente uma observação fica armazenada. Uma repetição após reiniciar mantém o ID do recibo. Repetição já armazenada não expira com a janela de entrada de leituras novas.

### R9 — HTTP 200 genérico liberava a sequência

O firmware exige JSON válido com ID positivo, status correspondente ao HTTP, dispositivo, boot e sequência exatos. Recibos têm limite de 1024 bytes e tamanho conhecido. Os casos C++ cobrem HTML, JSON malformado, identidade incorreta, sequência booleana/fracionária, status trocado e resposta excessiva.

### R10 — entregas atrasadas apareciam como observação atual

O painel seleciona pelo instante observado e distingue idade da observação de idade da última entrega armazenada. Também identifica relógio adiantado, sem atribuir precisão ou certificação ao sensor.

### R11 — entradas de autenticação e versão causavam comportamento incorreto

Chave incorreta com caracteres não ASCII retorna 401 controlado, em vez de 500. A versão deve ser um inteiro; `true` e `1.0` são rejeitados. Corpos maiores que 4096 bytes recebem 413. Importar a factory não cria banco implicitamente.

### R12 — painel apresentava contraste e rolagem por teclado insuficientes

O tom laranja foi ajustado; a tabela ganhou região focável com nome próprio. Cabeçalhos e identificadores de até 40 caracteres se adaptam a 320 px. O atalho foca o conteúdo inclusive sem JavaScript.

### Verificação desta revisão

- 17 testes Python aprovados no Windows;
- build ESP32 aprovado: 47.380 bytes de RAM e 927.885 bytes de aplicação;
- 9 testes Playwright aprovados; seis análises Axe sem violações;
- capturas em 1440 e 320 px inspecionadas;
- auditorias das dependências Python, incluindo PlatformIO 6.2.0, e Node sem vulnerabilidades conhecidas;
- 7 casos C++ nativos obrigatórios na CI Linux; execução local indisponível por ausência de gcc/g++;
- nenhuma medição física, carga em placa ou validação do parceiro executada nesta revisão.

## Parecer

O software e o firmware estão adequados para publicação como fundação técnica compilável e simulável. O PI V somente poderá ser apresentado como protótipo físico validado após montagem, ensaios, registro de evidências e participação real do parceiro.
