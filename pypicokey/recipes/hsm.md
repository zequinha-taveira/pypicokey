# Recipe: HSM (Hardware Security Module)

Documentação viva de como interagir com o Pico HSM. O pypicokey implementa suporte a dispositivos compatíveis com o padrão SmartCard-HSM.

## 1. Identificação
O Pico HSM é identificado pelo nome do leitor ou pelo ATR que contenha `SmartCard-HSM`.

## 2. Seleção do Applet
- **AID (SmartCard-HSM)**: `E8 28 BD 08 0F 01 4E 58 53 4D 10 01`
- **Comando APDU**: `00 A4 04 00 0C E8 28 BD 08 0F 01 4E 58 53 4D 10 01`

## 3. Comandos APDU Essenciais

### Obter Informações (GET DATA)
- **Device Information**: `00 CA 01 01 00`
- **Key List**: `00 CA 01 02 00`

### Login (VERIFY)
- **User PIN**: `00 20 00 81 [len] [pin]`
- **SO PIN (Admin)**: `00 20 00 82 [len] [pin]`

### Gestão de Chaves
- **Gerar Par de Chaves RSA**: `00 47 01 00 [params]`
- **Gerar Par de Chaves EC**: `00 47 02 00 [params]`

### Operações Criptográficas
- **Sign (PKCS#1 v1.5)**: `00 2A 9E 9A [len] [hash_data]`

### Reset de Fábrica (TERMINATE)
- **Command**: `00 04 00 00` (Apaga tudo e volta ao estado não inicializado)

## 4. Estrutura de Objetos
O HSM organiza chaves em slots ou "Key Domains". Cada chave possui um ID interno e metadados que podem ser lidos via comandos de exploração de sistema de arquivos (ISO 7816-4 EF/DF).
