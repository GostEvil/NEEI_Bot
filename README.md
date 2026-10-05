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

## Configuração Inicial

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Criar o ficheiro `.env`
Copia o `.env.example` para `.env` e preenche os valores:
```bash
cp .env.example .env
```

```env
DISCORD_TOKEN=o_teu_token_aqui
CLIENT_ID=o_teu_client_id_aqui
GUILD_ID=o_id_do_teu_servidor_aqui
MANAGER_IDS=teu_user_id,outro_manager_user_id
NEEI_ROLE_NAME=NEEI
```

### 3. Como obter os IDs necessários

**Token do Bot:**
1. Acede a [Discord Developer Portal](https://discord.com/developers/applications)
2. Cria/seleciona a tua aplicação → Aba "Bot" → "Reset Token"

**Client ID:**
- Developer Portal → Aba "OAuth2" → Client ID

**Guild ID (Servidor):**
- No Discord: Ativa o Modo de Programador (Definições → Avançado → Modo de Programador)
- Clica com o botão direito no servidor → "Copiar ID do servidor"

**User IDs (para MANAGER_IDS):**
- Com Modo de Programador ativo: clica com o botão direito num utilizador → "Copiar ID do utilizador"

### 4. Configurar o Discord Developer Portal
- Aba **Bot** → Ativa `SERVER MEMBERS INTENT`
- Aba **OAuth2 → URL Generator**:
  - Scopes: `bot` + `applications.commands`
  - Bot Permissions: `Manage Roles`
- Copia o link gerado e convida o bot para o servidor

### 5. Configurar Hierarquia de Cargos no Servidor
- Definições do Servidor → Cargos
- Arrasta o cargo do **bot** para **acima** do cargo **NEEI**

### 6. Arrancar o Bot
```bash
python bot.py
```

---

## Notas Importantes

- As mensagens de erro são **efémeras** (apenas visíveis para quem executou o comando).
- A lista de Admins é guardada automaticamente em `data/admins.json`.
- Para adicionar/remover Managers, edita diretamente o `.env` e reinicia o bot.
