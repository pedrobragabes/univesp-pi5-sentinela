# Guia de montagem experimental

## Materiais previstos

| Item | Quantidade | Observação |
|---|---:|---|
| ESP32 DevKit | 1 | placa compatível com `esp32dev` |
| sensor DHT22 | 1 | temperatura e umidade; não certificado |
| resistor 10 kΩ | 1 | pull-up entre dados e 3,3 V |
| protoboard e jumpers | 1 conjunto | montagem de bancada |
| cabo USB e fonte 5 V adequada | 1 | alimentação da placa pelo conector USB |
| referência de temperatura/umidade | 1 | necessária para comparação, a definir |

## Ligações propostas

```text
DHT22 VCC   -> ESP32 3V3
DHT22 DATA  -> ESP32 GPIO 4
DHT22 GND   -> ESP32 GND
10 kΩ       -> entre VCC e DATA
```

Confirme o pinout do módulo adquirido: sensores avulsos e placas DHT22 prontas podem ter ordens de pinos diferentes. Nunca aplique 5 V diretamente a um GPIO do ESP32. Desligue a alimentação antes de alterar a montagem.

## Preparação do firmware

1. copiar `firmware/include/local_config.example.h` para `local_config.h`;
2. definir SSID, senha, URL acessível a partir da rede do ESP32, chave e identificador;
3. compilar com `pio run -d firmware -e esp32dev`;
4. conectar a placa e enviar com `pio run -d firmware -e esp32dev -t upload`;
5. observar a serial em 115200 baud;
6. confirmar mensagens `reading_sent` e a leitura no painel.

`127.0.0.1` no ESP32 aponta para o próprio microcontrolador. Para alcançar o computador, use o IP local correto do computador e libere somente a porta necessária na rede de teste.

## Estado desta documentação

Este é um procedimento proposto e revisável, não um registro de montagem executada. Fotos, modelo exato do sensor, pinout confirmado, tensão medida e eventuais alterações devem ser anexados somente após a bancada real.
