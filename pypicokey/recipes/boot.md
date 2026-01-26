# Recipe: Pico Boot (Bootloader)

Documentação viva de como realizar atualizações de firmware no PicoKey.

## 1. Entrada no Modo Boot
Para entrar no modo bootloader (UF2):
- Conecte o dispositivo enquanto segura o PIN físico (se houver).
- Ou envie um comando de reinicialização para bootloader via HID/CCID (se suportado).

## 2. Identificação
O dispositivo aparece como um drive de armazenamento (Mass Storage Device) chamado `RPI-RP2`.

## 3. Arquivo de Informação
O arquivo `INFO_UF2.TXT` no drive contém metadados sobre o chip e a versão do bootloader.
Exemplo de conteúdo:
```text
UF2 Bootloader v3.0
Model: Raspberry Pi Pico
Board-ID: RPI-RP2
```

## 4. Atualização de Firmware
A atualização é feita copiando um arquivo `.uf2` para a raiz do drive.
O dispositivo detecta o arquivo, escreve na flash interna e reinicia automaticamente no modo normal.

## 5. Transparência no Processo
O pypicokey simplesmente automatiza a detecção do ponto de montagem e a cópia do arquivo, garantindo que o usuário não dependa de instaladores proprietários.
