# NEEI Bot 🤖

Bot de Discord para gestão do cargo **NEEI**.
Único bot que membros do NEEI tem acesso, o resto do **servidor foi feito por estudantes, para estudantes**

---

## Comandos Disponíveis

Igual ao `/help` do bot. Os comandos marcados com 🔒 têm restrições de permissão.

### 👤 Geral (todos)

| Comando | Descrição |
|---|---|
| `/help` | Mostra a ajuda do bot |
| `/verificacao1` | Verifica-te como aluno do IPB com o Certificado Multiusos |
| `/neei` | Lista os membros dos órgãos sociais do NEEI |
| `/calendario` | Adiciona eventos ao calendário (remover: 🔒 NEEI / Admins / Managers) |

### 🔒 Membros NEEI / Admins / Managers

| Comando | Descrição |
|---|---|
| `/listneei` | Lista os membros com a role NEEI |
| `/listadmin` | Lista os Admins e Managers do bot |

### 🛡️ Admins / Managers

| Comando | Descrição |
|---|---|
| `/neeigive` · `/neeiremove` | Atribui / remove a role NEEI |
| `/verify` · `/unverify` | Atribui / remove o cargo de verificação |
| `/sayimage` | Reenvia uma imagem para o canal configurado |
| `/logs` | Mostra os logs de ações por grupo |
| `/certconfig listyears` | Mostra os anos letivos aceites |

### 👑 Apenas Managers

| Comando | Descrição |
|---|---|
| `/admingive` · `/adminremove` | Dá / remove permissões de Admin do bot |
| `/config` | Define o cargo de verificação |
| `/configcalendario` | Define o canal onde o calendário é publicado |
| `/configsemestre` | Define o semestre ativo (1 ou 2) das disciplinas do calendário |
| `/certconfig addyear` · `removeyear` · `alertchannel` | Gere os anos letivos e o canal de alerta |
| `/delete` | Elimina um número de mensagens no canal |

### 📅 `/calendario`

Parâmetros: `tipo` (`add` / `remove`), `o_que` (`teste`, `trabalho`, `trabalho grupo`,
`exame intercalar`, `exame final`, `exame recurso`, `exame epoca especial`), `disciplina`
(sugestões do semestre ativo, separadas por ano), `data` (`DD/MM/AAAA`), `turno` (A–D, opcional)
e `observacoes` (opcional). O bot publica um embed no canal definido em `/configcalendario`;
sem canal configurado o comando não funciona.

## Hierarquia de Permissões

```
Managers (definidos no .env)
  └─▶ tudo, incluindo /admingive, /adminremove, /config*, /delete

Admins (geridos via /admingive)
  └─▶ /neeigive, /neeiremove, /verify, /unverify, /sayimage, /logs

Membros NEEI
  └─▶ /listneei, /listadmin, remover eventos do /calendario

Utilizadores Normais
  └─▶ /help, /verificacao1, /neei, adicionar eventos ao /calendario
```

## Notas Importantes

- As mensagens de erro são apenas visíveis para quem executou o comando.
- A lista de Admins é guardada automaticamente em `data/admins.json`.
- Para adicionar/remover Managers, edita diretamente o `.env` e reinicia o bot.
