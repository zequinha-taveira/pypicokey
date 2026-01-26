# Recipe: FIDO2 (CTAP2)

Documentação viva de como interagir com o Pico FIDO. O pypicokey prioriza a transparência na construção de pacotes.

## 1. Descoberta (USB HID)

O Pico FIDO é identificado via HID.
- **Vendor ID**: `0xFEFF` (ou `0x1209`)
- **Usage Page**: `0xF1D0` (FIDO Alliance)
- **Usage**: `0x01` (U2F/FIDO2)

## 2. Estrutura de Encapsulamento CTAPHID

Toda comunicação FIDO2 sobre USB utiliza pacotes de 64 bytes (ou o tamanho definido no descritor HID).

### Pacote de Inicialização (64 bytes)
| Offset | Tamanho | Descrição |
|--------|---------|-----------|
| 0      | 4       | Channel ID (CID) |
| 4      | 1       | Command (Bit 7 set = 1) |
| 5      | 1       | Payload Length High (BCNT) |
| 6      | 1       | Payload Length Low (BCNT) |
| 7-63   | 57      | Payload Data |

### Pacote de Continuação (64 bytes)
| Offset | Tamanho | Descrição |
|--------|---------|-----------|
| 0      | 4       | Channel ID (CID) |
| 4      | 1       | Packet Sequence (0x00 - 0x7F) |
| 5-63   | 59      | Payload Data |

## 3. Comandos CTAP2 Comuns

Os comandos são enviados no payload do `CTAPHID_CBOR` (0x10).

- **0x04 (authenticatorGetInfo)**: Retorna capacidades do dispositivo.
- **0x01 (authenticatorMakeCredential)**: Registro de nova chave.
- **0x02 (authenticatorGetAssertion)**: Autenticação/Login.
- **0x06 (authenticatorClientPIN)**: Gestão de PIN.
- **0x07 (authenticatorReset)**: Apaga todos os dados (requer presença física nos primeiros 10s após boot).

## 4. Exemplo de Iniciação de Canal
Para obter um CID (Channel ID), o cliente envia um comando `CTAPHID_INIT` (0x06) com um nonce de 8 bytes. O dispositivo responde com o mesmo nonce e o novo CID alocado.
