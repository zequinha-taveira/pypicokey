# Integração pypicokey ↔ pico-keys-sdk

## Visão Geral do Ecossistema Completo

O ecossistema Pico Keys agora está completo com três camadas totalmente abertas:

```
┌─────────────────────────────────────────────────────────────┐
│                    APLICAÇÕES DE USUÁRIO                     │
│  (GUIs, CLIs, Scripts Python, Ferramentas de Terceiros)     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      PYPIKOKEY                               │
│  Biblioteca Python que substitui ferramentas proprietárias   │
│  • Gerenciamento de dispositivos (manager.py)                │
│  • Protocolos: FIDO2, OpenPGP, HSM (protocol/)               │
│  • Módulos de funcionalidade (modules/)                      │
│  • Interface USB/HID/CCID (transport/)                       │
│  • CLI pronta para uso (cli/)                                │
└──────────────────────────┬──────────────────────────────────┘
                           │ USB (HID/CCID/Mass Storage)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   PICO-KEYS-SDK                              │
│  Firmware open-source para RP2040/RP2350                     │
│  • Implementação CTAP2/FIDO2                                 │
│  • Smart Card OpenPGP                                        │
│  • HSM com PKCS#11                                           │
│  • Bootloader UF2                                            │
│  • Criptografia (AES, RSA, ECC, Pós-quântica)               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    HARDWARE ABERTO                           │
│  • Raspberry Pi RP2040 / RP2350                              │
│  • Circuitos documentados                                    │
│  • Sem bloqueios de fabricante                               │
└─────────────────────────────────────────────────────────────┘
```

## Como a Integração Funciona

### 1. Descoberta de Dispositivos (`manager.py`)

O `PicoKeyManager` varre o sistema operacional em busca de dispositivos USB correspondendo aos IDs conhecidos:

```python
# Vendor/Product IDs definidos em constants.py
VendorID.PICOKEYS = 0x20A0
ProductID.PICO_FIDO = 0x42B2
ProductID.PICO_OPENPGP = 0x42C1
ProductID.PICO_HSM = 0x42D1
```

**Métodos de detecção:**
- **HID**: Para dispositivos FIDO2 (usage page 0xF1D0)
- **CCID**: Para smartcards OpenPGP e HSM (via pyscard)
- **USB Raw**: Para modo bootloader (Mass Storage)

### 2. Camada de Transporte (`transport/`)

#### HID (FIDO2)
```python
# Comunicação via pacotes de 64 bytes
# Usado pelo firmware CTAPHID no pico-keys-sdk
CTAPHID_CMD_INIT = 0x81
CTAPHID_CMD_MSG = 0x83
```

#### CCID (OpenPGP/HSM)
```python
# Comandos APDU padrão ISO 7816
# CLA INS P1 P2 LC DATA LE
# Exemplo: SELECT OpenPGP Applet
# 00 A4 04 00 06 D2 76 00 01 24 01
```

#### USB Mass Storage (Bootloader)
```python
# Copia de arquivo .uf2 para o dispositivo montado
# Reinicia o dispositivo para aplicar o firmware
```

### 3. Implementação de Protocolos (`protocol/`)

#### CTAP2 (FIDO2)
```python
# Comandos implementados:
CTAPCommand.AUTHENTICATOR_MAKE_CREDENTIAL = 0x01
CTAPCommand.AUTHENTICATOR_GET_ASSERTION = 0x02
CTAPCommand.AUTHENTICATOR_GET_INFO = 0x04
CTAPCommand.AUTHENTICATOR_CLIENT_PIN = 0x06
CTAPCommand.AUTHENTICATOR_RESET = 0x07
CTAPCommand.AUTHENTICATOR_CREDENTIAL_MANAGEMENT = 0x0A
```

**Correspondência com o firmware:**
- `pico-keys-sdk/src/ctap/` ↔ `pypicokey/protocol/ctap.py`
- Ambos implementam a especificação FIDO Alliance CTAP2

#### OpenPGP Smart Card
```python
# Instruções suportadas:
OpenPGPInstruction.SELECT = 0xA4
OpenPGPInstruction.VERIFY = 0x20
OpenPGPInstruction.GET_DATA = 0xCA
OpenPGPInstruction.PUT_DATA = 0xDA
OpenPGPInstruction.GENERATE_KEY = 0x47
OpenPGPInstruction.COMPUTE_SIGNATURE = 0x2A
```

**Correspondência com o firmware:**
- `pico-keys-sdk/src/openpgp/` ↔ `pypicokey/protocol/openpgp_apdu.py`
- Implementa OpenPGP Card Specification v2.x+v3.x

### 4. Módulos de Funcionalidade (`modules/`)

| Módulo | Funcionalidade | SDK Correspondente |
|--------|---------------|-------------------|
| `fido.py` | Registro/autenticação WebAuthn | `src/ctap/`, `src/fido/` |
| `openpgp.py` | Chaves GPG, assinatura, cifra | `src/openpgp/` |
| `hsm.py` | Geração de chaves, operações cripto | `src/hsm/`, `src/crypto/` |
| `boot.py` | Flash de firmware UF2 | `pico_sdk_import.cmake` |

### 5. Exemplo de Fluxo Completo

#### Cenário: Autenticação FIDO2

1. **Usuário executa script Python:**
```python
from pypicokey import PicoKeyManager

manager = PicoKeyManager()
device = manager.get_device_or_raise(mode="fido")
device.connect()

credential_id = device.fido.make_credential(
    rp={"id": "example.com", "name": "Example"},
    user={"id": b"user123", "name": "user@example.com"},
    challenge=b"random_challenge"
)
```

2. **pypicokey envia comando CTAP2 via HID:**
```
[0x83] [LEN] [CMD: 0x01 MAKE_CREDENTIAL] [CBOR payload...]
```

3. **pico-keys-sdk recebe no RP2040:**
```c
// src/ctap/ctap.c
int ctap_process_command(uint8_t cmd, uint8_t *data, size_t len) {
    case CTAP_MAKE_CREDENTIAL:
        return ctap_make_credential(data, len, response);
}
```

4. **Firmware gera chave ECC no hardware:**
```c
// src/crypto/ecc.c
ecc_generate_keypair(&private_key, &public_key);
```

5. **Resposta retorna ao Python:**
```python
{
    "fmt": "packed",
    "authData": b"...","attStmt": {...}
}
```

## Substituição de Ferramentas Proprietárias

### Antes (Vendor Lock-in)
```
Dispositivo → App Proprietário (pago/binário) → Usuário
                 ↑
           Código fechado
           Sem auditoria
           Dependência total
```

### Depois (Ecossistema Aberto)
```
Dispositivo ←→ pypicokey (MIT) ←→ Qualquer aplicação
                 ↑
           Código auditável
           Comunidade mantém
           Múltiplas GUIs possíveis
```

### Ferramentas Habilitadas pelo pypicokey

1. **SecureKey Manager (GUI Qt)**
   - Backend: `pypicokey`
   - Interface: PyQt6/PySide6
   - Substitui: PicoKey App proprietário

2. **CLI de Linha de Comando**
   ```bash
   picokey list
   picokey fido info
   picokey openpgp generate-key --type rsa4096
   picokey hsm init --pin 123456
   picokey flash firmware.uf2
   ```

3. **Scripts de Automação**
   ```python
   # Provisionamento em massa
   for device in manager.discover():
       device.provision(label=f"Key-{serial}")
       device.lock(admin_pin="secure_pin")
   ```

4. **Integração CI/CD**
   ```yaml
   # GitHub Actions
   - name: Test HSM
     run: |
       pip install pypicokey
       python tests/hsm_integration_test.py
   ```

## Vantagens da Arquitetura Aberta

### Para Usuários
- ✅ **Sem custo** de licenças de software
- ✅ **Auditoria completa** do código
- ✅ **Independência** de fornecedor único
- ✅ **Continuidade** garantida (comunidade mantém)

### Para Desenvolvedores
- ✅ **Backend reutilizável** para suas aplicações
- ✅ **Documentação viva** (recipes/)
- ✅ **Testabilidade** (suite de testes incluída)
- ✅ **Extensibilidade** (módulos plug-and-play)

### Para Pesquisadores
- ✅ **Transparência** total dos protocolos
- ✅ **Reprodutibilidade** de experimentos
- ✅ **Ensino** de criptografia prática
- ✅ **Experimentação** segura

## Casos de Uso Reais

### 1. Empresa de Tecnologia
**Problema:** Precisa provisionar 500 chaves de segurança para funcionários.

**Solução com pypicokey:**
```python
def provision_batch(serial_list, admin_pin):
    manager = PicoKeyManager()
    for serial in serial_list:
        device = manager.get_device_or_raise(serial=serial)
        device.connect()
        device.hsm.initialize(admin_pin=admin_pin)
        device.hsm.generate_key(label="corp-auth", key_type="ed25519")
        device.secure_lock(admin_pin=admin_pin)
        print(f"✅ {serial} provisionado")
```

### 2. Desenvolvedor de Aplicativo Desktop
**Problema:** Quer integrar autenticação FIDO2 no seu app Qt.

**Solução:**
```python
# backend_fido.py
class FidoBackend:
    def __init__(self):
        self.manager = PicoKeyManager()
    
    def authenticate(self, origin, challenge):
        device = self.manager.get_device_or_raise(mode="fido")
        assertion = device.fido.get_assertion(
            rp_id=origin,
            challenge=challenge
        )
        return assertion.to_dict()
```

### 3. Educador de Segurança
**Problema:** Ensinar criptografia assimétrica na prática.

**Solução:**
```python
# Aula prática: Gerando par de chaves RSA
from pypicokey import PicoKeyManager

mgr = PicoKeyManager()
key = mgr.get_device_or_raise(mode="openpgp")
key.connect()

# Gera chave diretamente no hardware (nunca sai do dispositivo!)
key.openpgp.generate_rsa_key(
    slot="SIGN",
    bits=4096,
    pin="123456"
)

print("Chave gerada no hardware - impossível extrair privada!")
```

## Compatibilidade com pico-keys-sdk

### Versões Suportadas

| pypicokey | pico-keys-sdk | Status |
|-----------|---------------|--------|
| 0.1.x | main (2024+) | ✅ Totalmente compatível |
| 0.1.x | branches antigas | ⚠️ Testar funcionalidades |

### Recursos Mapeados

| Recurso no SDK | Implementação no pypicokey | Status |
|---------------|---------------------------|--------|
| CTAPHID | `transport/hid.py` + `protocol/ctap.py` | ✅ Completo |
| OpenPGP Applet | `transport/ccid.py` + `protocol/openpgp_apdu.py` | ✅ Completo |
| HSM PKCS#11 | `modules/hsm.py` | ✅ Completo |
| PicoBoot UF2 | `modules/boot.py` | ✅ Completo |
| Criptografia PQ | `modules/hsm.py` (futuro) | 🔄 Em desenvolvimento |

## Contribuindo para o Ecossistema

### No Firmware (pico-keys-sdk)
```bash
cd pico-keys-sdk
mkdir build && cd build
cmake ..
make
```

### Na Biblioteca Python (pypicokey)
```bash
cd pypicokey
pip install -e ".[dev]"
## Matriz de Compatibilidade: `pypicokey` vs `pico-keys-sdk`

| Módulo / Funcionalidade | SDK (Firmware - C) | `pypicokey` (Host - Python) | Status | Notas de Implementação |
| :--- | :--- | :--- | :--- | :--- |
| **Transporte & Conexão** | | | | |
| Detecção USB (VID/PID) | `src/usb_descriptors.c` | `manager.py` (libusb/hidapi) | ✅ **Estável** | Suporte a hot-plug e múltiplos dispositivos. |
| Transporte HID | `src/usb_hid.c` | `transport/hid.py` | ✅ **Estável** | Comunicação bidirecional via reports HID. |
| Transporte CCID (SmartCard) | `src/usb_ccid.c` | `transport/ccid.py` | ✅ **Estável** | Emulação de leitora SmartCard via USB. |
| **Protocolos de Segurança** | | | | |
| FIDO2 / CTAP2 | `modules/fido2/` | `protocols/fido2.py` | ✅ **Estável** | Registro e Autenticação completos. Compatível com WebAuthn. |
| U2F (Legacy) | `modules/u2f/` | `protocols/u2f.py` | ✅ **Estável** | Retrocompatibilidade mantida. |
| OpenPGP Card v3 | `modules/openpgp/` | `modules/openpgp.py` | 🔄 **Em Dev** | Funções básicas (chaves RSA/ECC) ok; subchaves e atributos complexos em andamento. |
| PIV (NIST SP 800-73) | `modules/piv/` | `protocols/piv.py` | 🔄 **Em Dev** | Autenticação funcional; gerenciamento de certificados em expansão. |
| OTP (YubiKey compat.) | `src/otp/` | `modules/otp.py` | ⚠️ **Planejado** | Mapeamento APDU implementado; aguardando comandos específicos no firmware. |
| **Criptografia & HSM** | | | | |
| Geração de Chaves (On-board) | `src/crypto/` | Comandos via Protocolo | ✅ **Estável** | Chaves nunca saem do dispositivo (RSA, ECC). |
| Assinatura Digital | `src/crypto/` | Comandos via Protocolo | ✅ **Estável** | Suporte a SHA256, SHA384, SHA512. |
| Criptografia Pós-Quântica (PQ) | `modules/hsm.py` (futuro) | `modules/hsm.py` (esboço) | 🔴 **Futuro** | Algoritmos ML-KEM, ML-DSA, SLH-DSA definidos; aguardando maturação do SDK. |
| Vault Seguro (Storage) | `src/fs/` | `features/vault.py` | 🔄 **Em Dev** | Leitura/Escrita criptografada no flash do RP2040. |
| **Gerenciamento** | | | | |
| Bootloader / DFU | `src/bootloader/` | `tools/bootloader.py` | ✅ **Estável** | Atualização de firmware segura via USB. |
| Configuração de LED/Buzzer | `src/main.c` | `tools/config.py` | ✅ **Estável** | Feedback tátil e visual personalizável. |
| Wink (Identificação) | `src/main.c` | `manager.wink()` | ✅ **Estável** | Útil para identificar qual chave física conectar. |

### Legenda de Status
*   ✅ **Estável**: Funcionalidade completa, testada e pronta para produção.
*   🔄 **Em Dev**: Funcionalidade principal operante, mas recursos avançados ou edge-cases ainda em implementação.
*   ⚠️ **Planejado**: Arquitetura definida, código base iniciado, mas não funcional para o usuário final.
*   🔴 **Futuro**: Roadmap de longo prazo, dependente de evolução do SDK ou demanda da comunidade.

### Áreas Prioritárias para Contribuição

1.  **OpenPGP Avançado** (`modules/openpgp.py`)
    - [x] Implementar `get_public_key()` para leitura de chaves públicas por slot
    - [x] Implementar `generate_key()` com suporte a múltiplos algoritmos (RSA, ECC, Brainpool)
    - [ ] Implementar `reset_retry_counter()` com PIN de admin
    - [ ] Adicionar suporte a múltiplas chaves simultâneas (subkeys)
    - [ ] Implementar atributos estendidos de chave (touch policies, PIN policies)

2.  **Módulo OTP** (`modules/otp.py`)
    - [x] Criar estrutura completa do módulo OTP
    - [x] Mapear comandos APDU para configuração YubiKey-compatible
    - [x] Implementar HOTP (RFC 4226) com contador e validação
    - [ ] Integrar com firmware `src/otp/otp.c` para comandos específicos
    - [ ] Adicionar suporte a desafio-resposta (challenge-response)

3.  **Criptografia Pós-Quântica** (`modules/hsm.py`)
    - [x] Definir especificações de algoritmos PQ (ML-KEM, ML-DSA, SLH-DSA)
    - [x] Implementar interface `get_pq_algorithms()` para consulta
    - [x] Criar stubs para `generate_pq_key()`, `encapsulate()`, `sign_pq()`
    - [ ] Aguardar maturação do módulo `hsm.py` no pico-keys-sdk
    - [ ] Implementar interoperabilidade com bibliotecas PQ (liboqs)

## Guia de Contribuição para Ambos os Projetos

### Para o `pypicokey` (Python)

1. **Escolha uma Issue**: Veja as issues no GitHub marcadas com `good first issue` ou `help wanted`.
2. **Clone e Configure**:
   ```bash
   git clone https://github.com/polhenarejos/pypicokey.git
   cd pypicokey
   pip install -e ".[dev]"
   ```
3. **Implemente**: Siga os padrões de código (type hints, docstrings, logging).
4. **Teste**:
   ```bash
   pytest tests/
   black pypicokey tests
   ```
5. **Documente**: Adicione exemplos em `pypicokey/recipes/`.
6. **Submita**: Crie um Pull Request com descrição clara.

### Para o `pico-keys-sdk` (C/Firmware)

1. **Entenda a Arquitetura**: Leia `src/main.c` e `src/apdu.h`.
2. **Configure o Ambiente**:
   ```bash
   git clone https://github.com/polhenarejos/pico-keys-sdk.git
   cd pico-keys-sdk
   export PICO_SDK_PATH=/path/to/pico-sdk
   mkdir build && cd build
   cmake ..
   make
   ```
3. **Implemente**: Siga o estilo de código existente (indentação, naming conventions).
4. **Teste em Hardware**: Use um RP2040/RP2350 real.
5. **Documente**: Atualize comentários no código e README.
6. **Submita**: Crie um Pull Request explicando as mudanças.

### Integração entre Projetos

Ao contribuir em ambos, garanta que:
- Os comandos APDU no firmware correspondam aos esperados pelo `pypicokey`.
- As constantes e códigos de erro sejam consistentes.
- A documentação de integração seja atualizada.

## Conclusão

Com o **pypicokey**, o ciclo do ecossistema Pico Keys se fechou:

1. ✅ **Hardware Aberto** (RP2040/RP2350)
2. ✅ **Firmware Aberto** (pico-keys-sdk)
3. ✅ **Ferramentas Livres** (pypicokey)

Não há mais vendor lock-in. Não há mais dependência de aplicativos pagos ou pacotes órfãos. A comunidade agora tem controle total sobre todo o stack, do silício ao software.

---

**Made with ❤️ by the PicoKey Community**

*Liberte suas chaves. Libere sua criatividade.*
