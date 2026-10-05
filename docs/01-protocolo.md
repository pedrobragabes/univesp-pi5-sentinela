# Contrato de telemetria v1

## Transporte

- método: `POST`;
- rota: `/api/v1/readings`;
- conteúdo: `application/json`;
- autenticação: cabeçalho `X-Device-Key`;
- sucesso novo: HTTP 201, `status=accepted` e recibo correlacionado;
- repetição idempotente: HTTP 200, `status=duplicate` e o mesmo recibo;
- identidade já usada com conteúdo diferente: HTTP 409 e `status=conflict`;
- corpo acima de 4096 bytes: HTTP 413;
- credencial inválida: HTTP 401;
- mensagem inválida: HTTP 422.

HTTP foi escolhido para o MVP por permitir uma demonstração completa sem broker adicional. Em rede externa, o transporte deve obrigatoriamente ser protegido por HTTPS ou túnel confiável.

## Mensagem

```json
{
  "schema_version": 1,
  "device_id": "sentinela-demo-01",
  "boot_id": "51a7e1a0",
  "sequence": 17,
  "observed_at": 1786459200,
  "temperature_c_raw": 26.42,
  "temperature_c_filtered": 25.91,
  "humidity_pct_raw": 61.2,
  "humidity_pct_filtered": 60.6,
  "rssi_dbm": -58
}
```

| Campo | Regra |
|---|---|
| `schema_version` | inteiro igual a 1 |
| `device_id` | 3 a 40 caracteres em minúsculas, números ou hífen |
| `boot_id` | 8 dígitos hexadecimais, novo a cada inicialização |
| `sequence` | inteiro de 32 bits, incrementado após confirmação |
| `observed_at` | timestamp Unix UTC dentro de 24 horas do receptor |
| temperaturas | número finito entre -40 e 80 °C |
| umidades | número finito entre 0 e 100% |
| `rssi_dbm` | número entre -120 e 0 dBm |

Campos desconhecidos são rejeitados. A combinação `device_id + boot_id + sequence` é única. Se o servidor armazenar a mensagem, mas a resposta se perder, o dispositivo repete **o mesmo corpo, timestamp, valores e sequência** e recebe confirmação de duplicidade sem criar outra linha. A comparação é feita com os campos normalizados armazenados na mesma transação reservada do SQLite; um payload diferente recebe 409 e não altera a leitura original. Uma repetição já armazenada continua confirmável após 24 horas; somente leituras novas precisam estar dentro da janela temporal.

O recibo contém `id` inteiro positivo, `status`, `device_id`, `boot_id` e `sequence` inteira. Exemplo:

```json
{"id":1,"status":"accepted","device_id":"sentinela-demo-01","boot_id":"51a7e1a0","sequence":17}
```

O firmware exige o status correspondente ao código HTTP e todos os identificadores da leitura pendente. A resposta deve ter `Content-Length` de até 1024 bytes; respostas sem tamanho definido não são confirmadas nesta versão. Um 200 com HTML, um recibo truncado ou de outra leitura não incrementa a sequência.

A fila tem somente um slot em RAM. Não ocorre nova aquisição enquanto ele estiver ocupado. Reiniciar apaga o slot; não há persistência nem recuperação automática de leitura nova expirada ou de conflito permanente. Registre essa limitação nos ensaios de perda de rede/energia.

## Estado do painel

A observação exibida por dispositivo é a de maior `observed_at`, com desempate por recebimento e ID. `online` representa uma entrega armazenada nos últimos 120 segundos; `fresh` exige observação a até 120 segundos do relógio do servidor, em qualquer direção. Idade da observação e da entrega são separadas; observações futuras além desse limite mostram relógio adiantado. Esses indicadores são operacionais, sem certificação ou interpretação de saúde.

## Tratamento do sinal

O filtro usado é a média móvel exponencial:

```text
y[t] = α × x[t] + (1 - α) × y[t-1]
α = 0,25
```

A primeira amostra inicializa o filtro. Quanto menor o alfa, maior a suavização e o atraso. Valores brutos e filtrados são transmitidos para que o efeito possa ser comparado e auditado.

## Evolução

Uma alteração incompatível exige novo `schema_version`. O receptor atual rejeita versões desconhecidas em vez de interpretar silenciosamente campos com significado diferente.
