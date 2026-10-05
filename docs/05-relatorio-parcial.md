# Modelo de relatório parcial — PI V / PIE V

> O firmware compilado não comprova montagem física. Registre bancada, componentes e medições reais separadamente.

## Identificação, parceiro e problema

[PREENCHER]

## Requisitos do sistema físico

Descreva grandezas, faixas, precisão esperada, frequência de amostragem, alimentação, conectividade, ambiente e riscos. [PREENCHER]

## Arquitetura e componentes

Arquitetura implementada: firmware Arduino para `esp32dev`, sensor DHT22 proposto no GPIO 4, filtro EMA com alfa 0,25 e protocolo HTTP JSON v1. O receptor Flask 3.1.3 valida e armazena em SQLite; o painel mostra origem, estados e histórico. PlatformIO Core 6.2.0, plataforma espressif32 6.12.0, DHT library 1.4.6 e ArduinoJson 7.4.3 compõem o build. O slot de retransmissão é em RAM; sem confirmação, a aquisição pausa. Componentes adquiridos, pinout confirmado e datasheets da bancada: [PREENCHER após identificação do hardware].

## Estado do protótipo

| Evidência | Resultado | Situação |
|---|---|---|
| Compilação do firmware | ESP32 aprovado; RAM 47.380 B, aplicação 927.885 B | Software compilado em 05/10/2026; sem carga em placa |
| Testes do serviço | 17 Python aprovados; conflitos, concorrência e repetição após reinício | Dados sintéticos, sem sensor físico |
| Painel | 9 testes em 1440/390/320 px; 6 Axe sem violações | Foco e uso sem JavaScript verificados |
| Lógica C++ | 7 casos definidos na CI Linux | Compilador nativo ausente neste Windows |
| Montagem física | Não executada nesta preparação | Bloqueada até haver hardware |
| Calibração e teste prolongado | Não executados | Pendente |

## Protocolo de bancada e plano de ação

O [plano de validação física](03-validacao-fisica.md) propõe leitura básica, comparação, filtragem, desconexão, repetição, duração e consumo. O ensaio de retransmissão deverá conferir corpo imutável, pausa de aquisição, rejeição de colisão e perda do slot após reiniciar. Instrumentos, referência de calibração, período acordado, critérios de precisão e registros reais: [PREENCHER com equipe e parceiro].

## Referências

- [Contrato de telemetria do projeto](01-protocolo.md).
- [Revisão de código e evidências de software](04-revisao-de-codigo.md).
- [ArduinoJson 7 — deserializeJson](https://arduinojson.org/v7/api/json/deserializejson/).
- [ArduinoJson 7.4.3](https://github.com/bblanchon/ArduinoJson/releases/tag/v7.4.3).
- Datasheets dos componentes adquiridos e material do AVA: [PREENCHER].
