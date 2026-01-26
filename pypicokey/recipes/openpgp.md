# Recipe: OpenPGP

Documentação viva de como interagir com o Pico OpenPGP. O pypicokey segue a especificação OpenPGP Smartcard (v2.0, v3.0+).

## 1. Identificação (ATR)
O dispositivo é identificado pelo nome do leitor ("Pico OpenPGP") ou pelo ATR. 
Um ATR comum para dispositivos baseados em SmartCard-HSM ou OpenPGP de código aberto contém a string `OpenPGP` nos historical bytes.

## 2. Seleção do Applet
O primeiro passo é sempre selecionar o applet OpenPGP.
- **AID**: `D2 76 00 01 24 01`
- **Comando APDU**: `00 A4 04 00 06 D2 76 00 01 24 01`

## 3. Comandos APDU Essenciais

### Obter Dados (GET DATA)
Utilizado para ler metadados, versões e estado de PIN.
- **Application Related Data (0x6E)**: `00 CA 00 6E 00`
- **PW Status (Retries remaining)**: `00 CA 00 C4 00`
- **AID/Serial**: `00 CA 00 4F 00`

### Verificação de PIN (VERIFY)
- **User PIN (PW1)**: `00 20 00 81 [len] [pin_bytes]`
- **Admin PIN (PW3)**: `00 20 00 83 [len] [pin_bytes]`

### Reset de Fábrica (Sequence)
Para resetar um Pico OpenPGP (quando suportado):
1. Falhar o User PIN 3 vezes.
2. Falhar o Admin PIN 3 vezes.
3. Enviar comando `TERMINATE`: `00 E6 00 00`
4. Enviar comando `ACTIVATE`: `00 44 00 00`

## 4. Tags TLV Comuns
Os dados retornados pelo comando `6E` (Application Related Data) seguem o formato ASN.1 DER (TLV - Tag, Length, Value).
- `4F`: AID
- `5E`: Login Data
- `5F 52`: Historical Bytes (contém versão do firmware)
- `C4`: PW Status Byte
