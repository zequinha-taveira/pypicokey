# Manifesto pypicokey — Liberdade de Criar Ferramentas

## 1. Propósito do Projeto

O **pypicokey** é uma biblioteca Python open-source criada do zero para restaurar e preservar a **liberdade de criar ferramentas** em torno dos dispositivos PicoKeys (Pico FIDO, Pico OpenPGP, Pico HSM, Pico Boot).

O projeto surge após a remoção de bibliotecas Python anteriormente existentes, que eram utilizadas por ferramentas alternativas e educacionais, o que:

* enfraqueceu alternativas comunitárias;
* obscureceu a construção de comandos alternativos;
* aumentou a dependência de ferramentas únicas.

Este projeto existe para garantir que usuários, pesquisadores e desenvolvedores possam **entender, auditar, manter e criar suas próprias ferramentas**, de forma gratuita e transparente.

---

## 2. Princípios Fundamentais

1. **Liberdade de criar ferramentas**
   * Usuários devem poder construir CLIs, GUIs e scripts próprios.

2. **Nenhum código proprietário**
   * Todo o código é escrito do zero.
   * Apenas documentação pública e protocolos abertos são utilizados.

3. **Transparência acima de conveniência**
   * Nenhuma lógica “mágica” ou oculta.

4. **Deprecar, nunca apagar**
   * Compatibilidade e continuidade são prioridades.

5. **Projeto comunitário**
   * Forks, espelhos e mantenedores alternativos são encorajados.

---

## 3. Escopo Funcional

### 3.1 Escopo Inicial (MVP)
* Descoberta de dispositivos PicoKey via USB
* Identificação de modo (HID/FIDO, CCID/OpenPGP, HSM)
* Leitura de informações básicas do dispositivo
* API Python estável e documentada

### 3.2 Escopo Evolutivo
* Gerenciamento FIDO2
* Gerenciamento OpenPGP
* Gerenciamento HSM
* Suporte a PicoBoot

---

## 4. Legais e Éticos

* Nenhum código proprietário é copiado ou reutilizado.
* Apenas documentação pública é utilizada.
* Nenhuma engenharia reversa binária é realizada.
* O projeto respeita licenças e limites legais.

---

## 5. Resultado Esperado

* Biblioteca Python aberta e auditável.
* Alternativa gratuita ao PicoKey App.
* Base para ferramentas independentes.
* Continuidade e confiança no ecossistema.

---

**Made with ❤️ by the PicoKey Community**
