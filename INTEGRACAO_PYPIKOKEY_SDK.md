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
pytest
black pypicokey tests
```

### Documentação Viva (Recipes)
Adicione exemplos práticos em `pypicokey/recipes/`:
- `fido.md` - Receitas FIDO2
- `openpgp.md` - Receitas OpenPGP
- `hsm.md` - Receitas HSM

## Conclusão

Com o **pypicokey**, o ciclo do ecossistema Pico Keys se fechou:

1. ✅ **Hardware Aberto** (RP2040/RP2350)
2. ✅ **Firmware Aberto** (pico-keys-sdk)
3. ✅ **Ferramentas Livres** (pypicokey)

Não há mais vendor lock-in. Não há mais dependência de aplicativos pagos ou pacotes órfãos. A comunidade agora tem controle total sobre todo o stack, do silício ao software.

---

**Made with ❤️ by the PicoKey Community**

*Liberte suas chaves. Libere sua criatividade.*
