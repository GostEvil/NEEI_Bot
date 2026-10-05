# NEEI Bot 🤖

Bot de Discord para gestão do cargo **NEEI** com sistema de permissões internas.
Único bot que membros do NEEI tem acesso, o resto do **servidor foi feito por estudantes, para estudantes**

---

## Comandos Disponíveis

| Comando | Descrição | Quem pode usar |
|---|---|---|
| `/neeigive @user` | Atribui a role NEEI ao utilizador | Admins |
| `/neeiremove @user` | Remove a role NEEI do utilizador | Admins |
| `/admingive @user` | Dá permissões de Admin do bot | Apenas Managers |
| `/adminremove @user` | Remove permissões de Admin do bot | Apenas Managers |
| `/verificacao1 @user` | Submeter certificado para obter verificacao1 | All |
| `/logs` | Ver as logs de cargos | Admin + Manager |
| `/neei`| Mostra as pessoas que se encontram no Nucleo (tags, nome, numMeca)| All |
| `/neeigive`| Adicionar pessoa ao NEEI (add tag) | Admin |
| `/neeiremove`| Remover pessoa do NEEI (remove tag) | Admin |

## Hierarquia de Permissões

```
Managers (definidos no .env)
  └─▶ /admingive, /adminremove, /neeigive, /neeiremove

Admins (geridos via /admingive)
  └─▶ /neeigive, /neeiremove

Utilizadores Normais
  └─▶ /neei
```

## Notas Importantes

- As mensagens de erro são **efémeras** (apenas visíveis para quem executou o comando).
- A lista de Admins é guardada automaticamente em `data/admins.json`.
- Para adicionar/remover Managers, edita diretamente o `.env` e reinicia o bot.
