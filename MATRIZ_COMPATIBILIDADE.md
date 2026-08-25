# Matriz de Compatibilidade: pypicokey vs pico-keys-sdk

> **Nota:** Esta matriz será atualizada continuamente conforme novas versões do `pypicokey` e do `pico-keys-sdk` forem lançadas.
> 
> Última atualização: **Dezembro 2024**
> Versões de referência: `pypicokey >= 0.3.0` | `pico-keys-sdk >= 1.5.0`

---

## 📋 Visão Geral

Esta documentação técnica mapeia a compatibilidade entre o firmware **pico-keys-sdk** (escrito em C para RP2040/RP2350) e a biblioteca host **pypicokey** (Python). Ela serve como guia para desenvolvedores, integradores e usuários finais entenderem quais funcionalidades estão disponíveis, estáveis ou em desenvolvimento.

### Legenda de Status

| Símbolo | Status | Significado |
| :---: | :--- | :--- |
| ✅ | **Estável** | Funcionalidade completa, testada e pronta para produção. |
| 🔄 | **Em Desenvolvimento** | Funcionalidade principal operante, mas recursos avançados ou *edge-cases* ainda em implementação. |
| ⚠️ | **Planejado** | Arquitetura definida, código base iniciado, mas não funcional para o usuário final. |
| 🔴 | **Futuro / Roadmap** | Dependente de evolução futura do SDK ou demanda da comunidade. |
| ❌ | **Incompatível** | Funcionalidade existente em um lado mas sem suporte no outro (bloqueio temporário). |

---

## 🔌 1. Transporte e Conexão

A camada fundamental que permite a comunicação física e lógica entre o host (PC/Servidor) e o dispositivo (RP2040/RP2350).

| Funcionalidade | Módulo SDK (Firmware) | Módulo pypicokey (Host) | Status | Notas de Implementação |
| :--- | :--- | :--- | :---: | :--- |
| **Detecção USB (VID/PID)** | `src/usb_descriptors.c` | `manager.py` (hidapi/libusb) | ✅ | Suporte a *hot-plug*, múltiplos dispositivos e filtros por serial. |
| **Transporte HID** | `src/usb_hid.c` | `transport/hid.py` | ✅ | Comunicação bidirecional via reports HID (64 bytes). Padrão FIDO/U2F. |
| **Transporte CCID** | `src/usb_ccid.c` | `transport/ccid.py` | ✅ | Emulação de leitora SmartCard. Necessário para OpenPGP/PIV. |
| **Bootloader (DFU)** | `src/bootloader/` | `tools/bootloader.py` | ✅ | Atualização de firmware segura. Modos UF2 e DFU suportados. |
| **Wink (Identificação)** | `src/main.c` | `device.wink()` | ✅ | Pisca LED para identificar fisicamente o dispositivo correto. |

---

## 🔐 2. Protocolos de Segurança

Implementação dos padrões industriais de autenticação e criptografia.

| Protocolo | Módulo SDK (Firmware) | Módulo pypicokey (Host) | Status | Notas de Implementação |
| :--- | :--- | :--- | :---: | :--- |
| **FIDO2 / CTAP2** | `modules/fido2/` | `protocols/fido2.py` | ✅ | Registro (*MakeCredential*) e Autenticação (*GetAssertion*). Compatível com WebAuthn. |
| **U2F (Legacy)** | `modules/u2f/` | `protocols/u2f.py` | ✅ | Retrocompatibilidade para serviços que não suportam FIDO2 completo. |
| **OpenPGP Card v3** | `modules/openpgp/` | `protocols/openpgp.py` | 🔄 | **Foco Atual:** Suporte a chaves RSA/ECC básicas. <br>🚧 *Em progresso:* Múltiplas chaves, atributos complexos e subchaves. |
| **PIV (NIST SP 800-73)** | `modules/piv/` | `protocols/piv.py` | 🔄 | Autenticação funcional. Gerenciamento de certificados e chaves privadas em expansão. |
| **OTP (YubiCompat)** | `modules/otp/` | `protocols/otp.py` | ⚠️ | **Foco Atual:** Estrutura de comandos APDU mapeada. <br>🚧 *Em progresso:* Configuração de slots HOTP/TOTP e acesso por senha. |

---

## 🛡️ 3. Criptografia e HSM

Funcionalidades de baixo nível para operações criptográficas e armazenamento seguro.

| Funcionalidade | Módulo SDK (Firmware) | Módulo pypicokey (Host) | Status | Notas de Implementação |
| :--- | :--- | :--- | :---: | :--- |
| **Geração de Chaves** | `src/crypto/` | Via Comandos de Protocolo | ✅ | Geração on-board (RSA-2048/4096, ECC P-256/P-384). Chave privada nunca expõe. |
| **Assinatura Digital** | `src/crypto/` | Via Comandos de Protocolo | ✅ | Suporte a hashes SHA256, SHA384, SHA512. Operações RSA e ECDSA. |
| **Vault Seguro** | `src/fs/` | `features/vault.py` | 🔄 | Leitura/Escrita criptografada na flash interna do RP2040. |
| **Criptografia PQ** | `modules/hsm.py` (futuro) | `crypto/pq.py` (esboço) | 🔴 | **Roadmap:** Algoritmos ML-KEM (Kyber) e ML-DSA (Dilithium). Aguardando maturidade do módulo HSM no SDK. |

---

## 🎯 Áreas Prioritárias para Contribuição

Se você deseja contribuir com código, testes ou documentação, foque nestas três áreas críticas identificadas para a próxima versão:

### 1. OpenPGP Avançado (`protocols/openpgp.py`)
*   **Objetivo:** Implementar suporte nativo a múltiplas chaves de autenticação e criptografia simultâneas.
*   **Tarefas:**
    *   Expandir o parser de respostas APDU para lidar com múltiplos slots de chaves.
    *   Implementar comandos `GENERATE KEY` para curvas elípticas específicas (Brainpool, Curve25519).
    *   Adicionar suporte a PINs diferenciados (Admin, User, Signing).
*   **Arquivo SDK de Referência:** `modules/openpgp/openpgp.c`

### 2. Módulo OTP (`protocols/otp.py`)
*   **Objetivo:** Mapear completamente os comandos APDU do módulo `otp` do SDK para a interface Python.
*   **Tarefas:**
    *   Implementar a estrutura de comandos `SET_SLOT`, `GET_CODE`, `ERASE_SLOT`.
    *   Criar utilitários para conversão de seeds (Base32/Hex) para o formato binário do dispositivo.
    *   Adicionar suporte a *Access Codes* para proteção dos slots.
*   **Arquivo SDK de Referência:** `modules/otp/otp.c`

### 3. Criptografia Pós-Quântica (`crypto/pq.py`)
*   **Objetivo:** Definir padrões de interoperabilidade para algoritmos pós-quânticos assim que o módulo `hsm.py` no SDK estiver maduro.
*   **Tarefas:**
    *   Estabelecer a troca de mensagens para encapsulamento/desencapsulamento (KEM).
    *   Definir formatos de chave pública/privada para ML-KEM e ML-DSA.
    *   Criar testes de vetor (test vectors) para validar a implementação contra referências do NIST.
*   **Arquivo SDK de Referência:** `modules/hsm/hsm.c` (Em desenvolvimento)

---

## 🔄 Processo de Atualização da Matriz

Para manter este documento preciso, siga o fluxo abaixo ao lançar novas versões:

1.  **Release do SDK:** Quando uma nova tag for criada em [pico-keys-sdk](https://github.com/polhenarejos/pico-keys-sdk), verifique o `CHANGELOG` por novos módulos ou mudanças de API.
2.  **Implementação no pypicokey:** Após a detecção de mudança, crie uma *Issue* no repositório `pypicokey` para rastrear a implementação correspondente.
3.  **Testes de Integração:** Execute a suíte de testes `tests/test_compatibility.py` para validar o par SDK/pypicokey.
4.  **Atualização do Documento:**
    *   Altere o status na tabela acima.
    *   Atualize as "Notas de Implementação".
    *   Incremente a data de "Última atualização".

---

## 🤝 Guia Rápido de Contribuição

Quer ajudar a mover um item de "🔄 Em Desenvolvimento" para "✅ Estável"?

1.  **Escolha uma tarefa** da seção "Áreas Prioritárias".
2.  **Clone ambos os repositórios:**
    ```bash
    git clone https://github.com/polhenarejos/pico-keys-sdk.git
    git clone https://github.com/seu-usuario/pypicokey.git
    ```
3.  **Ambiente de Teste:**
    *   Compile o firmware com as flags de debug ativadas.
    *   Use o `pypicokey` em modo verbose (`logging.basicConfig(level=logging.DEBUG)`) para inspecionar os pacotes APDU.
4.  **Envie um PR:** Inclua testes unitários que provem a compatibilidade com o firmware.

---

*Documento mantido pela comunidade Pico Keys. Licença: CC-BY-SA 4.0*
