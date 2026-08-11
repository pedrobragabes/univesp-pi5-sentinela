# Plano de validação física

Este plano ainda não foi executado. Ele define previamente o que deverá ser medido quando os componentes e o parceiro estiverem disponíveis.

## Ensaios mínimos

| Ensaio | Procedimento | Evidência | Critério preliminar |
|---|---|---|---|
| leitura básica | 20 amostras em condição estável | serial, banco e foto da bancada | nenhuma leitura fora da faixa válida |
| comparação | posicionar DHT22 e referência lado a lado por 60 min | série pareada e erro absoluto | relatar erro médio; limite final depende do uso acordado |
| filtragem | introduzir pequena variação controlada | curvas bruta e filtrada | reduzir dispersão, declarando o atraso criado |
| perda de rede | desligar Wi-Fi por 3 min e religar | log e estado do painel | sem travamento; estado muda para sem sinal e volta após reconexão |
| repetição | reenviar uma sequência já aceita | resposta e contagem no banco | nenhuma linha duplicada |
| duração | operar pelo período acordado, inicialmente 2 h | início/fim, falhas e contagem | taxa de entrega calculada, sem alegação antes do ensaio |
| consumo | medir corrente em repouso e transmissão | instrumento, método e valores | resultado apenas descritivo no MVP |

## Registro obrigatório

- data, local e responsáveis;
- modelo e identificação dos equipamentos;
- versões do firmware e do serviço;
- condição ambiental e intervalo de amostragem;
- amostras esperadas, recebidas, inválidas e perdidas;
- cálculo usado para erro e dispersão;
- incidentes, mudanças e limitações;
- aceite e interpretação do parceiro, quando aplicável.

Não se deve converter a especificação nominal do fabricante em “resultado medido”. Precisão, autonomia e confiabilidade só poderão ser declaradas depois dos respectivos ensaios.
