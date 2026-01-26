# Recipe: FIDO2 (CTAP2)

Documentação viva de como interagir com o Pico FIDO.

## Conceitos
O Pico FIDO utiliza o protocolo CTAP2 (Client to Authenticator Protocol) sobre USB HID.

## Fluxo de Descoberta (USB HID)
- Vendor ID: `0xFEFF` (ou `0x1209`)
- Usage Page: `0xF1D0`
- Usage: `0x01`

## Comandos CTAP2 Comuns
- `0x01` - AUTHENTICATOR_MAKE_CREDENTIAL
- `0x02` - AUTHENTICATOR_GET_ASSERTION
- `0x04` - AUTHENTICATOR_GET_INFO
- `0x06` - AUTHENTICATOR_CLIENT_PIN
- `0x07` - AUTHENTICATOR_RESET

*Mais detalhes em breve.*
