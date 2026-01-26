# Recipe: OpenPGP

Documentação viva de como interagir com o Pico OpenPGP.

## Conceitos
O Pico OpenPGP emula um smartcard ISO/IEC 7816-4 e implementa a especificação OpenPGP Smartcard.

## Identificação (ATR)
O dispositivo pode ser identificado pelo ATR (Answer To Reset) ou pelo nome do leitor (ex: "Pico OpenPGP").

## Comandos APDU Básicos
- Selecionar OpenPGP Applet: `00 A4 04 00 06 D2 76 00 01 24 01`

*Mais detalhes em breve.*
