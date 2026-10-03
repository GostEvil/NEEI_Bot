# TODO — NEEI Bot

## Verificação 2 / Integração com segundo bot

> ⚠️ A Verificação 2 **NÃO** está implementada neste bot.  
> Será executada por um **segundo bot separado**.  
> Este ficheiro documenta tudo o que é necessário para a futura integração.

---

### Contexto

O sistema de verificação está dividido em duas fases independentes:

| Fase | Bot | Método |
|------|-----|--------|
| **Verificação 1** | Este bot (NEEI Bot) | Certificado Multiusos do IPB enviado via Discord |
| **Verificação 2** | Segundo bot (a criar) | Autenticação pelo sistema interno do IPB |

Apenas após **ambas** as verificações serem concluídas com sucesso é que o utilizador é considerado **verificado**.

---

### O que o segundo bot deverá fazer (Verificação 2)

1. Autenticar o aluno através do sistema interno do IPB (ex: portal académico, OAuth institucional, etc.).
2. Obter, no mínimo, os seguintes dados do utilizador autenticado:
   - **Discord User ID** (passado pelo utilizador ou obtido via OAuth)
   - **Nome completo**
   - **Número mecanográfico** (ex: `a63426`)
   - Outros dados conforme necessário (curso, ano letivo, etc.)
3. Confirmar a autenticação e registar o resultado.

---

### Cruzamento entre Verificação 1 e Verificação 2

A chave principal recomendada para cruzamento é o **número mecanográfico**.

Fluxo esperado:

```
Verificação 1 (este bot):
    Discord User ID → número mecanográfico → certificado válido

Verificação 2 (segundo bot):
    Discord User ID → número mecanográfico → login válido

Cruzamento:
    Se número mecanográfico da V1 == número mecanográfico da V2:
        → MATCH → utilizador verificado
    Caso contrário:
        → MISMATCH → rejeitar / pedir revisão manual
```

---

### Arquitectura recomendada para integração futura

#### Opção A — Base de dados partilhada (simples)
- Ambos os bots escrevem os resultados numa base de dados partilhada (ex: SQLite, PostgreSQL).
- Um processo externo ou um dos bots faz o cruzamento.

#### Opção B — API REST interna (escalável)
- Criar uma API REST interna (ex: FastAPI) que:
  - Recebe os resultados da V1 e da V2
  - Faz o cruzamento
  - Notifica o Discord com o resultado final
- O NEEI Bot ficaria preparado para enviar o resultado da V1 para esta API.

#### Opção C — Ficheiro JSON local (desenvolvimento apenas)
- Apenas para testes/desenvolvimento.
- Cada bot escreve um ficheiro JSON com os seus resultados.
- Não recomendado para produção.

> **Recomendação**: Opção A ou B para produção.

---

### Dados que o NEEI Bot já guarda após a Verificação 1

Após uma Verificação 1 bem-sucedida, os seguintes dados ficam disponíveis no log do canal privado:

| Campo | Descrição |
|-------|-----------|
| `discord_user_id` | ID Discord do utilizador |
| `name` | Nome completo extraído do certificado |
| `mechanographic_number` | Número mecanográfico (ex: `a63426`) |
| `identification_document` | Número do documento de identificação |
| `course` | Curso (`Engenharia Informática`) |
| `institution` | Instituição (`Instituto Politécnico de Bragança`) |
| `nickname` | Nickname atribuído no Discord |
| `timestamp` | Data/hora da verificação |

Para a integração futura, estes dados deverão ser persistidos numa base de dados
(não apenas no canal de log) para que o segundo bot possa consultá-los.

---

### O que falta implementar para a integração completa

- [ ] Persistir o resultado da V1 numa base de dados (actualmente só é enviado para o canal de log).
- [ ] Implementar o segundo bot com autenticação pelo sistema interno do IPB.
- [ ] Criar o mecanismo de cruzamento entre V1 e V2 (ver opções acima).
- [ ] Definir o que acontece quando há MATCH:
  - Atribuir cargo de verificado?
  - Enviar mensagem de boas-vindas?
  - Notificar um administrador?
- [ ] Definir o que acontece quando há MISMATCH (nome diferente, número diferente, etc.).
- [ ] Definir timeout: o que acontece se V1 for concluída mas V2 nunca for?
- [ ] Definir se a V1 pode ser repetida (ex: aluno envia certificado errado).
- [ ] Definir política de privacidade para os dados persistidos.

---

### Notas de Segurança para a integração futura

- O número do documento de identificação **não deve** ser transmitido para o segundo bot.
- O cruzamento deve ser feito apenas com o número mecanográfico e o Discord User ID.
- Os dados pessoais devem ser encriptados em repouso se persistidos em base de dados.
- O segundo bot deve autenticar-se perante qualquer API partilhada (não deixar endpoints abertos).

---

### Referência rápida — estrutura do resultado da Verificação 1

```python
# Resultado interno após verify_certificate() com sucesso:
{
    "valid": True,
    "name": "Nuno Miguel Silva",
    "mechanographic_number": "a63426",
    "identification_document": "12345678",
    "course": "Engenharia Informática",
    "institution": "Instituto Politécnico de Bragança",
    "nickname": "Nuno Silva (a63426)"
}

# Em caso de falha:
{
    "valid": False,
    "reason": "..."  # motivo genérico, sem dados pessoais
}
```

---

*Última actualização: 2026-10-03*
