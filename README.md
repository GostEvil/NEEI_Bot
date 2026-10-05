# NEEI Bot 🤖

Bot de Discord para gestão do cargo **NEEI** com sistema de permissões internas em 3 níveis.

---

## Estrutura do Projeto

```
NEEI_Bot/
├── bot.py            # Ficheiro principal do bot (todos os comandos)
├── config.py         # Carregamento de variáveis de ambiente (.env)
├── data_manager.py   # Persistência dos admins (admins.json)
├── requirements.txt  # Dependências Python
├── .env              # Variáveis secretas (NÃO partilhar!)
├── .env.example      # Exemplo do .env
├── .gitignore
└── data/
    └── admins.json   # Criado automaticamente pelo bot
```

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

---

## Hierarquia de Permissões

```
Managers (definidos no .env)
  └─▶ /admingive, /adminremove, /neeigive, /neeiremove

Admins (geridos via /admingive)
  └─▶ /neeigive, /neeiremove

Utilizadores Normais
  └─▶ /neei
```

---

## Notas Importantes

- As mensagens de erro são **efémeras** (apenas visíveis para quem executou o comando).
- A lista de Admins é guardada automaticamente em `data/admins.json`.
- Para adicionar/remover Managers, edita diretamente o `.env` e reinicia o bot.
