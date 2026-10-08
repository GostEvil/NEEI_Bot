import discord
from discord import app_commands
from discord.ext import commands
import datetime

import config
import data_manager
from subjects import SUBJECTS, subject_label, subjects_for_semester
from verificacao1 import register_verificacao1


# ─────────────────────────────────────────────────────────────
# Setup do Bot
# ─────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True  # Necessário para gerir membros e roles

bot = commands.Bot(command_prefix="!", intents=intents)
guild_obj = discord.Object(id=config.get_guild_id())

# Registar o comando /verificacao1 (módulo independente)
register_verificacao1(bot, guild_obj)


# ─────────────────────────────────────────────────────────────
# Helpers de Permissão
# ─────────────────────────────────────────────────────────────

def user_is_manager(interaction: discord.Interaction) -> bool:
    """Verifica se o utilizador que executou o comando é um Manager."""
    return config.is_manager(str(interaction.user.id))


def user_is_admin_or_manager(interaction: discord.Interaction) -> bool:
    """Verifica se o utilizador é Admin (bot) ou Manager (.env)."""
    uid = str(interaction.user.id)
    return config.is_manager(uid) or data_manager.is_admin(uid)


async def get_neei_role(guild: discord.Guild) -> discord.Role | None:
    """Procura e retorna a role NEEI no servidor. Retorna None se não existir."""
    role_name = config.get_neei_role_name()
    return discord.utils.get(guild.roles, name=role_name)


def user_has_neei_role(interaction: discord.Interaction) -> bool:
    """Verifica se o utilizador tem o cargo NEEI no servidor."""
    role_name = config.get_neei_role_name()
    return any(role.name == role_name for role in interaction.user.roles)


def get_user_role(interaction: discord.Interaction) -> str:
    """Retorna o nível de permissão do utilizador associado à interação."""
    uid = str(interaction.user.id)
    if config.is_manager(uid):
        return "manager"
    elif data_manager.is_admin(uid):
        return "admin"
    elif user_has_neei_role(interaction):
        return "neei"
    return "user"


async def get_verify_role(guild: discord.Guild) -> discord.Role | None:
    """Procura e retorna o cargo de verificação no servidor. Retorna None se não configurado."""
    role_id = config.get_verify_role_id()
    if role_id:
        return guild.get_role(role_id)
    return None


# ─────────────────────────────────────────────────────────────
# Eventos do Bot
# ─────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    """Executado quando o bot conecta ao Discord com sucesso."""
    try:
        # Sincroniza os slash commands apenas para o servidor definido (mais rápido)
        synced = await bot.tree.sync(guild=guild_obj)
        print(f"✅ Bot '{bot.user}' online!")
        print(f"📋 {len(synced)} comando(s) slash sincronizados.")
        print(f"🔑 Managers carregados: {config.get_manager_ids()}")
        print("🛠️ Commands registered:", [c.name for c in bot.tree.get_commands()])
    except Exception as e:
        print(f"Error syncing commands: {e}")


# ─────────────────────────────────────────────────────────────
# Comandos: NEEI Role (/neeigive e /neeiremove)
# ─────────────────────────────────────────────────────────────

@bot.tree.command(
    name="neeigive",
    description="Atribui a role NEEI a um utilizador. (Apenas Admins/Managers)",
    guild=guild_obj,
)
@app_commands.describe(user="O utilizador ao qual vai ser atribuída a role NEEI")
async def neeigive(interaction: discord.Interaction, user: discord.Member):
    # 1. Verificar permissão de quem invocou o comando
    if not user_is_admin_or_manager(interaction):
        await interaction.response.send_message(
            "❌ Não tens permissão para usar este comando.",
            ephemeral=True,  # Apenas visível para quem executou
        )
        return

    # 2. Obter a role NEEI no servidor
    role = await get_neei_role(interaction.guild)
    if role is None:
        await interaction.response.send_message(
            f"❌ Não foi encontrado nenhum cargo chamado **'{config.get_neei_role_name()}'** neste servidor.\n"
            "Verifica se o cargo existe e se o nome no `.env` está correto.",
            ephemeral=True,
        )
        return

    # 3. Verificar se o utilizador já tem a role
    if role in user.roles:
        await interaction.response.send_message(
            f"⚠️ {user.mention} já tem o cargo **{role.name}**.",
            ephemeral=True,
        )
        return

    # 4. Atribuir a role
    try:
        await user.add_roles(role, reason=f"Atribuído por {interaction.user} via /neeigive")
        await interaction.response.send_message(
            f"✅ Cargo **{role.name}** atribuído com sucesso a {user.mention}!"
        )
        data_manager.add_log(str(interaction.user.id), get_user_role(interaction), "neeigive", str(user.id), "Atribuiu cargo NEEI")
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ O bot não tem permissões suficientes para gerir este cargo.\n"
            "Garante que o cargo do bot está **acima** do cargo NEEI na hierarquia do servidor.",
            ephemeral=True,
        )
    except discord.HTTPException as e:
        await interaction.response.send_message(
            f"❌ Ocorreu um erro inesperado: `{e}`",
            ephemeral=True,
        )


@bot.tree.command(
    name="neeiremove",
    description="Remove a role NEEI de um utilizador. (Apenas Admins/Managers)",
    guild=guild_obj,
)
@app_commands.describe(user="O utilizador ao qual vai ser removida a role NEEI")
async def neeiremove(interaction: discord.Interaction, user: discord.Member):
    # 1. Verificar permissão de quem invocou o comando
    if not user_is_admin_or_manager(interaction):
        await interaction.response.send_message(
            "❌ Não tens permissão para usar este comando.",
            ephemeral=True,
        )
        return

    # 2. Obter a role NEEI no servidor
    role = await get_neei_role(interaction.guild)
    if role is None:
        await interaction.response.send_message(
            f"❌ Não foi encontrado nenhum cargo chamado **'{config.get_neei_role_name()}'** neste servidor.",
            ephemeral=True,
        )
        return

    # 3. Verificar se o utilizador realmente tem a role
    if role not in user.roles:
        await interaction.response.send_message(
            f"⚠️ {user.mention} não tem o cargo **{role.name}** para remover.",
            ephemeral=True,
        )
        return

    # 4. Remover a role
    try:
        await user.remove_roles(role, reason=f"Removido por {interaction.user} via /neeiremove")
        await interaction.response.send_message(
            f"✅ Cargo **{role.name}** removido com sucesso de {user.mention}."
        )
        data_manager.add_log(str(interaction.user.id), get_user_role(interaction), "neeiremove", str(user.id), "Removeu cargo NEEI")
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ O bot não tem permissões suficientes para gerir este cargo.",
            ephemeral=True,
        )
    except discord.HTTPException as e:
        await interaction.response.send_message(
            f"❌ Ocorreu um erro inesperado: `{e}`",
            ephemeral=True,
        )


# ─────────────────────────────────────────────────────────────
# Comandos: Admin Interno (/admingive e /adminremove)
# ─────────────────────────────────────────────────────────────

@bot.tree.command(
    name="admingive",
    description="Dá permissões de Admin do bot a um utilizador. (Apenas Managers)",
    guild=guild_obj,
)
@app_commands.describe(user="O utilizador que vai receber permissões de Admin do bot")
async def admingive(interaction: discord.Interaction, user: discord.Member):
    # 1. Apenas Managers podem usar este comando
    if not user_is_manager(interaction):
        await interaction.response.send_message(
            "❌ Apenas os **Managers** podem usar este comando.",
            ephemeral=True,
        )
        return

    # 2. Impedir que um Manager se adicione a si próprio (já tem permissões superiores)
    if config.is_manager(str(user.id)):
        await interaction.response.send_message(
            f"⚠️ {user.mention} já é um **Manager** e tem permissões superiores.",
            ephemeral=True,
        )
        return

    # 3. Adicionar à lista de admins
    added = data_manager.add_admin(str(user.id))
    if not added:
        await interaction.response.send_message(
            f"⚠️ {user.mention} já é um **Admin** do bot.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"✅ {user.mention} foi adicionado como **Admin** do bot com sucesso!\n"
        f"Agora pode usar `/neeigive` e `/neeiremove`."
    )
    data_manager.add_log(str(interaction.user.id), get_user_role(interaction), "admingive", str(user.id), "Adicionou como Admin")


@bot.tree.command(
    name="adminremove",
    description="Remove as permissões de Admin do bot de um utilizador. (Apenas Managers)",
    guild=guild_obj,
)
@app_commands.describe(user="O utilizador ao qual vão ser removidas as permissões de Admin")
async def adminremove(interaction: discord.Interaction, user: discord.Member):
    # 1. Apenas Managers podem usar este comando
    if not user_is_manager(interaction):
        await interaction.response.send_message(
            "❌ Apenas os **Managers** podem usar este comando.",
            ephemeral=True,
        )
        return

    # 2. Não é possível remover um Manager via este comando
    if config.is_manager(str(user.id)):
        await interaction.response.send_message(
            f"⚠️ {user.mention} é um **Manager** e não pode ser removido por este comando.\n"
            "Para remover um Manager, edita diretamente o ficheiro `.env`.",
            ephemeral=True,
        )
        return

    # 3. Remover da lista de admins
    removed = data_manager.remove_admin(str(user.id))
    if not removed:
        await interaction.response.send_message(
            f"⚠️ {user.mention} não é um **Admin** do bot.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"✅ Permissões de **Admin** do bot removidas de {user.mention} com sucesso."
    )
    data_manager.add_log(str(interaction.user.id), get_user_role(interaction), "adminremove", str(user.id), "Removeu Admin")


# ─────────────────────────────────────────────────────────────
# Comandos: Verificação (/verify, /unverify e /config)
# ─────────────────────────────────────────────────────────────

@bot.tree.command(
    name="verify",
    description="Atribui o cargo de verificação a um utilizador. (Apenas Admins/Managers)",
    guild=guild_obj,
)
@app_commands.describe(user="O utilizador a ser verificado")
async def verify(interaction: discord.Interaction, user: discord.Member):
    if not user_is_admin_or_manager(interaction):
        await interaction.response.send_message(
            "❌ Não tens permissão para usar este comando.",
            ephemeral=True,
        )
        return

    role = await get_verify_role(interaction.guild)
    if role is None:
        await interaction.response.send_message(
            "❌ O cargo de verificação não está configurado. Os Managers devem usar `/config`.",
            ephemeral=True,
        )
        return

    if role in user.roles:
        await interaction.response.send_message(
            f"⚠️ {user.mention} já tem o cargo de verificação **{role.name}**.",
            ephemeral=True,
        )
        return

    try:
        await user.add_roles(role, reason=f"Verificado por {interaction.user} via /verify")
        await interaction.response.send_message(
            f"✅ O cargo **{role.name}** foi atribuído a {user.mention} com sucesso!"
        )
        data_manager.add_log(str(interaction.user.id), get_user_role(interaction), "verify", str(user.id), "Verificou utilizador")
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ O bot não tem permissões para gerir o cargo de verificação. Verifica a hierarquia de cargos.",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Ocorreu um erro: `{e}`", ephemeral=True)


@bot.tree.command(
    name="unverify",
    description="Remove o cargo de verificação de um utilizador. (Apenas Admins/Managers)",
    guild=guild_obj,
)
@app_commands.describe(user="O utilizador a perder a verificação")
async def unverify(interaction: discord.Interaction, user: discord.Member):
    if not user_is_admin_or_manager(interaction):
        await interaction.response.send_message(
            "❌ Não tens permissão para usar este comando.",
            ephemeral=True,
        )
        return

    role = await get_verify_role(interaction.guild)
    if role is None:
        await interaction.response.send_message(
            "❌ O cargo de verificação não está configurado. Os Managers devem usar `/config`.",
            ephemeral=True,
        )
        return

    if role not in user.roles:
        await interaction.response.send_message(
            f"⚠️ {user.mention} não tem o cargo de verificação **{role.name}**.",
            ephemeral=True,
        )
        return

    try:
        await user.remove_roles(role, reason=f"Removido por {interaction.user} via /unverify")
        await interaction.response.send_message(
            f"✅ A verificação foi removida de {user.mention}."
        )
        data_manager.add_log(str(interaction.user.id), get_user_role(interaction), "unverify", str(user.id), "Removeu verificação")
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ O bot não tem permissões para gerir o cargo de verificação.",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Ocorreu um erro: `{e}`", ephemeral=True)


@bot.tree.command(
    name="config",
    description="Configura o cargo de verificação. (Apenas Managers)",
    guild=guild_obj,
)
@app_commands.describe(role="O cargo que será atribuído na verificação")
async def config_command(interaction: discord.Interaction, role: discord.Role):
    if not user_is_manager(interaction):
        await interaction.response.send_message(
            "❌ Apenas os **Managers** podem usar este comando.",
            ephemeral=True,
        )
        return

    try:
        config.set_verify_role_id(role.id)
        data_manager.add_log(str(interaction.user.id), get_user_role(interaction), "config", None, f"Configurou cargo verificação para {role.id}")
        await interaction.response.send_message(
            f"✅ O cargo de verificação foi configurado para **{role.mention}** com sucesso!"
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Ocorreu um erro ao guardar a configuração no `.env`: `{e}`",
            ephemeral=True,
        )


# ─────────────────────────────────────────────────────────────
# Comandos: Listagens (/listadmin e /listneei)
# ─────────────────────────────────────────────────────────────

@bot.tree.command(
    name="listadmin",
    description="Mostra todos os Admins e Managers do bot. (Apenas membros NEEI/Admins/Managers)",
    guild=guild_obj,
)
async def listadmin(interaction: discord.Interaction):
    # 1. Verificar permissão — cargo NEEI, Admin ou Manager
    if not (user_has_neei_role(interaction) or user_is_admin_or_manager(interaction)):
        await interaction.response.send_message(
            "❌ Apenas membros com o cargo **NEEI** podem usar este comando.",
            ephemeral=True,
        )
        return

    guild = interaction.guild
    manager_ids = config.get_manager_ids()
    admin_ids = data_manager.load_admins()

    # 2. Construir linhas de Managers
    manager_lines = []
    for uid in manager_ids:
        member = guild.get_member(int(uid))
        if member:
            manager_lines.append(f"👑 {member.mention} (`{member.name}`)")
        else:
            manager_lines.append(f"👑 ID: `{uid}` *(não encontrado no servidor)*")

    # 3. Construir linhas de Admins
    admin_lines = []
    for uid in admin_ids:
        member = guild.get_member(int(uid))
        if member:
            admin_lines.append(f"🛡️ {member.mention} (`{member.name}`)")
        else:
            admin_lines.append(f"🛡️ ID: `{uid}` *(não encontrado no servidor)*")

    # 4. Construir embed
    embed = discord.Embed(
        title="📋 Lista de Admins do Bot",
        color=discord.Color.gold(),
    )
    embed.add_field(
        name=f"👑 Managers ({len(manager_lines)})",
        value="\n".join(manager_lines) if manager_lines else "*Nenhum manager definido.*",
        inline=False,
    )
    embed.add_field(
        name=f"🛡️ Admins ({len(admin_lines)})",
        value="\n".join(admin_lines) if admin_lines else "*Nenhum admin adicionado ainda.*",
        inline=False,
    )
    embed.set_footer(text="Managers são definidos no .env | Admins via /admingive")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="listneei",
    description="Mostra todos os membros com a role NEEI. (Apenas membros NEEI/Admins/Managers)",
    guild=guild_obj,
)
async def listneei(interaction: discord.Interaction):
    # 1. Verificar permissão — cargo NEEI, Admin ou Manager
    if not (user_has_neei_role(interaction) or user_is_admin_or_manager(interaction)):
        await interaction.response.send_message(
            "❌ Apenas membros com o cargo **NEEI** podem usar este comando.",
            ephemeral=True,
        )
        return

    # 2. Obter a role NEEI
    role = await get_neei_role(interaction.guild)
    if role is None:
        await interaction.response.send_message(
            f"❌ Não foi encontrado nenhum cargo chamado **'{config.get_neei_role_name()}'** neste servidor.",
            ephemeral=True,
        )
        return

    # 3. Listar membros com a role
    members_with_role = role.members

    if not members_with_role:
        await interaction.response.send_message(
            f"📋 Nenhum membro tem atualmente o cargo **{role.name}**.",
            ephemeral=True,
        )
        return

    # 4. Construir embed (limite de 25 por campo do Discord)
    lines = [f"• {m.mention} (`{m.name}`)" for m in members_with_role]

    embed = discord.Embed(
        title=f"📋 Membros com o cargo {role.name}",
        description="\n".join(lines[:25]),  # Limite de segurança do Discord
        color=role.color if role.color.value != 0 else discord.Color.blue(),
    )
    embed.set_footer(text=f"Total: {len(members_with_role)} membro(s)")

    # Se houver mais de 25, adiciona nota
    if len(members_with_role) > 25:
        embed.add_field(
            name="⚠️ Lista truncada",
            value=f"*Existem {len(members_with_role)} membros no total. Apenas os primeiros 25 são mostrados.*",
            inline=False,
        )

    await interaction.response.send_message(embed=embed)


# Data estruturada dos membros do NEEI organizada por orgãos
NEEI_STRUCTURE = [
    {
        "organ": "Mesa Assembleia",
        "members": [
            {"role": "Presidente", "name": "João Pedro Esteves Caldas", "num": "a64716"},
            {"role": "1º secretário", "name": "Carolina Garcia Fernandes", "num": "a59445"},
            {"role": "2° Secretário", "name": "Nuno José Freitas da Silva", "num": "a63426"},
        ],
    },
    {
        "organ": "Direção",
        "members": [
            {"role": "Presidente", "name": "Daniel Filipe Campos Coelho", "num": "a54457"},
            {"role": "Vice-Presidente", "name": "Luís Carlos Miranda Fernandes", "num": "a50765"},
            {"role": "Tesoureiro", "name": "Vítor Hugo da Silva Monteiro", "num": "a60862"},
            {"role": "1° Secretário", "name": "Joana dos Santos Moreira", "num": "a63416"},
            {"role": "2° Secretario", "name": "Artur Gonçalo Teixeira Pinheiro", "num": "a60325"},
            {"role": "1°Vogal", "name": "Inês Freitas", "num": "a60838"},
            {"role": "2° Vogal", "name": "Lara Sebastião Lopes", "num": "a68015"},
            {"role": "3° Vogal", "name": "João André Pereira Rodrigues", "num": "a67357"},
            {"role": "4° Vogal", "name": "Gonçalo Filipe Pedrosa Pereira", "num": "a59451"},
            {"role": "5° Vogal", "name": "Tiago David Gonçalves Tomás", "num": "a64725"},
            {"role": "6° Vogal", "name": "Carlos Miguel Gomes Moreira", "num": "a56547"},
        ],
    },
    {
        "organ": "Conselho Fiscal",
        "members": [
            {"role": "Presidente", "name": "Francisco José da Silva Morais", "num": "a60556"},
            {"role": "Vice-Presidente", "name": "Diogo José Teixeira de Sousa", "num": "a55726"},
            {"role": "Relator", "name": "Pedro Miguel Coelho Ribeiro", "num": "a60850"},
        ],
    },
]


@bot.tree.command(
    name="neei",
    description="Mostra a lista dos membros dos órgãos sociais do NEEI.",
    guild=guild_obj,
)
async def neei(interaction: discord.Interaction):
    guild = interaction.guild
    import re

    all_members = guild.members

    embed = discord.Embed(
        title="🏛️ Órgãos Sociais do NEEI",
        color=discord.Color.blue(),
    )

    total_membros = 0

    for organ_info in NEEI_STRUCTURE:
        lines = []
        for item in organ_info["members"]:
            role_title = item["role"]
            name = item["name"]
            num = item["num"]
            num_digits = num.lstrip("aA")
            pattern = re.compile(re.escape(num_digits), re.IGNORECASE)

            matched_member = None
            if all_members:
                for m in all_members:
                    if pattern.search(m.display_name) or pattern.search(m.name):
                        matched_member = m
                        break

            user_mention = matched_member.mention if matched_member else "@utilizador"
            discord_tag = f" (`{matched_member.name}`)" if matched_member else ""

            # Exemplo de linha: - **Presidente:** @User João Silva (a60000) (`username`)
            lines.append(f"• **{role_title}:** {user_mention} {name} ({num}){discord_tag}")
            total_membros += 1

        embed.add_field(
            name=f"📌 {organ_info['organ']}",
            value="\n".join(lines),
            inline=False
        )

    embed.set_footer(text=f"Total: {total_membros} membro(s)")

    # Desativa pings/notificações para utilizadores e roles mencionadas no Embed
    allowed_mentions = discord.AllowedMentions(users=False, roles=False, everyone=False)

    await interaction.response.send_message(
        embed=embed,
        allowed_mentions=allowed_mentions
    )


# ─────────────────────────────────────────────────────────────
# Comando: Ajuda (/help)
# ─────────────────────────────────────────────────────────────

@bot.tree.command(
    name="help",
    description="Mostra a ajuda do bot: o que faz e a lista de comandos.",
    guild=guild_obj,
)
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Ajuda — Bot NEEI",
        description=(
            "Bot do **NEEI** para verificação de alunos do IPB, gestão de "
            "cargos, calendário de eventos e registo de ações.\n"
            "Os comandos marcados com 🔒 têm restrições de permissão."
        ),
        color=discord.Color.blue(),
    )

    embed.add_field(
        name="👤 Geral",
        value=(
            "`/help` — Mostra esta mensagem.\n"
            "`/verificacao1` — Verifica-te como aluno do IPB com o Certificado Multiusos.\n"
            "`/neei` — Lista os membros dos órgãos sociais do NEEI."
        ),
        inline=False,
    )
    embed.add_field(
        name="🔒 Membros NEEI / Admins / Managers",
        value=(
            "`/listneei` — Lista os membros com a role NEEI.\n"
            "`/listadmin` — Lista os Admins e Managers do bot."
        ),
        inline=False,
    )
    embed.add_field(
        name="🛡️ Admins / Managers",
        value=(
            "`/neeigive` · `/neeiremove` — Atribui / remove a role NEEI.\n"
            "`/verify` · `/unverify` — Atribui / remove o cargo de verificação.\n"
            "`/calendario` — Adiciona ou remove eventos do calendário.\n"
            "`/sayimage` — Reenvia uma imagem para o canal configurado.\n"
            "`/logs` — Mostra os logs de ações por grupo.\n"
            "`/certconfig listyears` — Mostra os anos letivos aceites."
        ),
        inline=False,
    )
    embed.add_field(
        name="👑 Apenas Managers",
        value=(
            "`/admingive` · `/adminremove` — Dá / remove permissões de Admin do bot.\n"
            "`/config` — Define o cargo de verificação.\n"
            "`/configcalendario` — Define o canal do calendário.\n"
            "`/certconfig addyear` · `removeyear` · `alertchannel` — Gere anos letivos e canal de alerta.\n"
            "`/delete` — Elimina um número de mensagens no canal."
        ),
        inline=False,
    )
    embed.set_footer(text="Usa / para ver a descrição e os parâmetros de cada comando.")

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ─────────────────────────────────────────────────────────────
# Comando: Enviar Imagem via Bot (/sayimage)
# ─────────────────────────────────────────────────────────────

@bot.tree.command(
    name="sayimage",
    description="Reenvia uma imagem para o canal configurado como se fosse o bot. (Apenas Admins/Managers)",
    guild=guild_obj,
)
@app_commands.describe(
    imagem="A imagem a reenviar pelo bot",
)
async def sayimage(
    interaction: discord.Interaction,
    imagem: discord.Attachment,
):

    # 1. Verificar permissões (Admins/Managers)
    if not user_is_admin_or_manager(interaction):
        await interaction.response.send_message(
            "❌ Não tens permissão para usar este comando.",
            ephemeral=True,
        )
        return

    # 2. Verificar se o ficheiro anexado é realmente uma imagem
    if not (imagem.content_type and imagem.content_type.startswith("image/")):
        await interaction.response.send_message(
            "⚠️ O ficheiro enviado não parece ser uma imagem válida.",
            ephemeral=True,
        )
        return

    # 3. Determinar o canal de destino (do .env ou o canal atual)
    target_channel_id = config.get_target_channel_id()
    target_channel = interaction.channel

    if target_channel_id:
        found_channel = interaction.guild.get_channel(target_channel_id)
        if found_channel:
            target_channel = found_channel
        else:
            try:
                target_channel = await interaction.guild.fetch_channel(target_channel_id)
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Não foi possível encontrar o canal com ID `{target_channel_id}` definido no `.env`.",
                    ephemeral=True,
                )
                return

    # 4. Converter a imagem enviada para um discord.File
    try:
        image_file = await imagem.to_file()
    except discord.HTTPException as e:
        await interaction.response.send_message(
            f"❌ Não foi possível descarregar a imagem: `{e}`", ephemeral=True
        )
        return

    # 5. Enviar apenas a imagem no canal de destino
    try:
        await target_channel.send(file=image_file)
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ O bot não tem permissão para enviar mensagens nesse canal.",
            ephemeral=True,
        )
        return
    except discord.HTTPException as e:
        await interaction.response.send_message(
            f"❌ Ocorreu um erro ao enviar a imagem: `{e}`", ephemeral=True
        )
        return
    data_manager.add_log(str(interaction.user.id), get_user_role(interaction), "sayimage", None, "Enviou imagem como bot")

    # 6. Responder de forma privada (ephemeral) confirmando o envio
    await interaction.response.send_message(
        f"✅ Imagem enviada com sucesso no canal {target_channel.mention}!",
        ephemeral=True,
    )



# ─────────────────────────────────────────────────────────────
# Comando: Eliminar Mensagens (/delete)
# ─────────────────────────────────────────────────────────────

@bot.tree.command(
    name="delete",
    description="Elimina um número específico de mensagens no canal. (Apenas Managers)",
    guild=guild_obj,
)
@app_commands.describe(quantidade="O número de mensagens a eliminar (máx: 100)")
async def delete_messages(interaction: discord.Interaction, quantidade: int):
    # 1. Apenas Managers
    if not user_is_manager(interaction):
        await interaction.response.send_message(
            "❌ Apenas os **Managers** podem usar este comando.",
            ephemeral=True,
        )
        return

    # 2. Validar quantidade
    if quantidade < 1 or quantidade > 100:
        await interaction.response.send_message(
            "⚠️ A quantidade deve estar entre 1 e 100.",
            ephemeral=True,
        )
        return

    # 3. Eliminar as mensagens
    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=quantidade)
        data_manager.add_log(str(interaction.user.id), get_user_role(interaction), "delete", None, f"Eliminou {len(deleted)} mensagens")
        await interaction.followup.send(
            f"✅ Foram eliminadas **{len(deleted)}** mensagens com sucesso!",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ O bot não tem permissões (`Manage Messages`) para eliminar mensagens neste canal.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"❌ Ocorreu um erro: `{e}`",
            ephemeral=True
        )


# ─────────────────────────────────────────────────────────────
# Comando: Logs (/logs)
# ─────────────────────────────────────────────────────────────

@bot.tree.command(
    name="logs",
    description="Mostra logs de ações por grupo (manager, admin, neei).",
    guild=guild_obj,
)
@app_commands.describe(grupo="O grupo cujas logs queres ver (manager, admin, neei, all para todos)", pagina="Número da página (padrão 1)")
@app_commands.choices(grupo=[
    app_commands.Choice(name="Managers", value="manager"),
    app_commands.Choice(name="Admins", value="admin"),
    app_commands.Choice(name="NEEI", value="neei"),
    app_commands.Choice(name="All", value="all"),
])
async def logs_command(interaction: discord.Interaction, grupo: str, pagina: int = 1):
    if not user_is_admin_or_manager(interaction):
        await interaction.response.send_message("❌ Não tens permissão para usar este comando.", ephemeral=True)
        return

    # Mapear o valor para o nome para apresentação
    group_names = {"manager": "Managers", "admin": "Admins", "neei": "NEEI", "all": "All", ".": "All"}
    # Em discord.py 2.x, grupo pode vir como str ou Choice dependendo do type hint.
    # Por segurança, caso venha como Choice, extraímos o value:
    group_val = getattr(grupo, "value", grupo)
    group_name = group_names.get(group_val, "Desconhecido")

    logs = data_manager.get_logs()
    filtered_logs = []
    
    for log in logs:
        match = False
        if group_val == "manager":
            if log.get("actor_role") == "manager":
                match = True
        elif group_val == "admin":
            if log.get("actor_role") == "admin" or log.get("action") in ["admingive", "adminremove"]:
                match = True
        elif group_val == "neei":
            if log.get("actor_role") == "neei" or log.get("action") in ["neeigive", "neeiremove"]:
                match = True
        elif group_val == "all":
            match = True

        if match:
            filtered_logs.append(log)
            
    if not filtered_logs:
        await interaction.response.send_message(f"📋 Não existem logs para a categoria **{group_name}**.", ephemeral=False)
        return
        
    # Build all lines (most recent first)
    lines = []
    for log in reversed(filtered_logs):
        try:
            dt = datetime.datetime.fromisoformat(log["timestamp"]).strftime("%d/%m %H:%M")
        except (KeyError, TypeError, ValueError):
            dt = str(log.get("timestamp", "??"))
        actor = f"<@{log.get('actor_id', '?')}>"
        target = f" -> <@{log['target_id']}>" if log.get("target_id") else ""
        details = f" ({log['details']})" if log.get("details") else ""
        action = f"**{log.get('action', '?')}**"
        line = f"`[{dt}]` {actor} {action}{target}{details}"
        lines.append(line)
    
    # Pagination (25 linhas por página)
    try:
        page = int(pagina)
    except:
        page = 1
    if page < 1:
        page = 1
    total_pages = (len(lines) + 24) // 25 or 1
    if page > total_pages:
        page = total_pages
    start_idx = (page - 1) * 25
    end_idx = start_idx + 25
    page_lines = lines[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"📋 Logs: {group_name} (página {page}/{total_pages})",
        color=discord.Color.light_grey()
    )
    embed.description = "\n".join(page_lines)
    
    await interaction.response.send_message(embed=embed, ephemeral=False)


# ─────────────────────────────────────────────────────────────
# Comandos: Configuração da Verificação 1 (/certconfig)
# ─────────────────────────────────────────────────────────────

cert_config_group = app_commands.Group(
    name="certconfig",
    description="Configuração da Verificação 1 — anos letivos e canal de alerta.",
)
bot.tree.add_command(cert_config_group, guild=guild_obj)


@cert_config_group.command(
    name="addyear",
    description="Adiciona um ano letivo aceite na Verificação 1. (Apenas Managers)",
)
@app_commands.describe(ano="Ano letivo no formato AAAA/AAAA (ex: 2025/2026)")
async def certconfig_addyear(interaction: discord.Interaction, ano: str):
    if not user_is_manager(interaction):
        await interaction.response.send_message(
            "❌ Apenas os **Managers** podem usar este comando.", ephemeral=True
        )
        return

    import re
    m = re.fullmatch(r"([0-9]{4})/([0-9]{4})", ano.strip())
    if not m or int(m.group(2)) != int(m.group(1)) + 1:
        await interaction.response.send_message(
            "⚠️ Formato inválido. Usa o formato `AAAA/AAAA` com anos consecutivos "
            "(ex: `2025/2026`).",
            ephemeral=True,
        )
        return

    year = ano.strip()
    added = data_manager.add_allowed_year(year)
    if not added:
        await interaction.response.send_message(
            f"⚠️ O ano letivo **{year}** já está na lista.", ephemeral=True
        )
        return

    data_manager.add_log(
        str(interaction.user.id), get_user_role(interaction),
        "certconfig_addyear", None, f"Adicionou ano letivo: {year}"
    )
    years = data_manager.get_allowed_years()
    await interaction.response.send_message(
        f"✅ Ano letivo **{year}** adicionado.\n"
        f"Anos aceites atualmente: **{', '.join(years)}**"
    )


@cert_config_group.command(
    name="removeyear",
    description="Remove um ano letivo da lista de anos aceites. (Apenas Managers)",
)
@app_commands.describe(ano="Ano letivo a remover (ex: 2025/2026)")
async def certconfig_removeyear(interaction: discord.Interaction, ano: str):
    if not user_is_manager(interaction):
        await interaction.response.send_message(
            "❌ Apenas os **Managers** podem usar este comando.", ephemeral=True
        )
        return

    year = ano.strip()
    removed = data_manager.remove_allowed_year(year)
    if not removed:
        await interaction.response.send_message(
            f"⚠️ O ano letivo **{year}** não está na lista.", ephemeral=True
        )
        return

    data_manager.add_log(
        str(interaction.user.id), get_user_role(interaction),
        "certconfig_removeyear", None, f"Removeu ano letivo: {year}"
    )
    years = data_manager.get_allowed_years()
    anos_str = ", ".join(years) if years else "*nenhum — verificação de ano desativada*"
    await interaction.response.send_message(
        f"✅ Ano letivo **{year}** removido.\n"
        f"Anos aceites atualmente: **{anos_str}**"
    )


@cert_config_group.command(
    name="listyears",
    description="Mostra os anos letivos aceites na Verificação 1. (Apenas Admins/Managers)",
)
async def certconfig_listyears(interaction: discord.Interaction):
    if not user_is_admin_or_manager(interaction):
        await interaction.response.send_message(
            "❌ Não tens permissão para usar este comando.", ephemeral=True
        )
        return

    years = data_manager.get_allowed_years()
    alert_ch_id = data_manager.get_cert_alert_channel_id()
    alert_ch_str = f"<#{alert_ch_id}>" if alert_ch_id else "*não configurado*"

    embed = discord.Embed(
        title="⚙️ Configuração da Verificação 1",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="📅 Anos Letivos Aceites",
        value="\n".join(f"• **{y}**" for y in years) if years
              else "*Nenhum configurado — verificação de ano desativada.*",
        inline=False,
    )
    embed.add_field(
        name="🔔 Canal de Alerta (ano inválido)",
        value=alert_ch_str,
        inline=False,
    )
    embed.set_footer(text="Use /certconfig addyear e /certconfig alertchannel para configurar.")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@cert_config_group.command(
    name="alertchannel",
    description="Define o canal de alerta para certificados com ano letivo inválido. (Apenas Managers)",
)
@app_commands.describe(canal="Canal onde os alertas de ano inválido serão enviados")
async def certconfig_alertchannel(interaction: discord.Interaction, canal: discord.TextChannel):
    if not user_is_manager(interaction):
        await interaction.response.send_message(
            "❌ Apenas os **Managers** podem usar este comando.", ephemeral=True
        )
        return

    data_manager.set_cert_alert_channel_id(canal.id)
    data_manager.add_log(
        str(interaction.user.id), get_user_role(interaction),
        "certconfig_alertchannel", None, f"Definiu canal de alerta: {canal.id}"
    )
    await interaction.response.send_message(
        f"✅ Canal de alerta configurado para {canal.mention}.\n"
        "Quando alguém enviar um certificado com ano letivo inválido, será enviado um alerta aqui."
    )


# ─────────────────────────────────────────────────────────────
# Comando: Calendário de avaliações (/calendario)
# ─────────────────────────────────────────────────────────────

CALENDAR_KINDS = {
    "teste": "Teste",
    "trabalho": "Trabalho",
    "trabalho grupo": "Trabalho de grupo",
    "exame intercalar": "Exame intercalar",
    "exame final": "Exame final",
    "exame recurso": "Exame de recurso",
    "exame epoca especial": "Exame de época especial",
}


@bot.tree.command(
    name="calendario",
    description="Adiciona um evento ao calendário (todos) ou remove-o (NEEI+).",
    guild=guild_obj,
)
@app_commands.describe(
    tipo="Adicionar ou remover o evento",
    o_que="Tipo de avaliação",
    disciplina="Disciplina do semestre ativo (escreve para pesquisar)",
    data="Data no formato DD/MM/AAAA",
)
@app_commands.choices(
    tipo=[
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove"),
    ],
    o_que=[app_commands.Choice(name=k, value=k) for k in CALENDAR_KINDS],
)
async def calendario(
    interaction: discord.Interaction,
    tipo: str,
    o_que: str,
    disciplina: str,
    data: str,
):
    if tipo == "remove" and get_user_role(interaction) == "user":
        await interaction.response.send_message(
            "❌ Apenas membros **NEEI**, Admins ou Managers podem remover eventos.",
            ephemeral=True,
        )
        return

    try:
        date = datetime.datetime.strptime(data.strip(), "%d/%m/%Y").date()
    except ValueError:
        await interaction.response.send_message(
            "⚠️ Data inválida. Usa o formato `DD/MM/AAAA` (ex: `25/01/2027`).",
            ephemeral=True,
        )
        return

    subject = disciplina.strip()
    semester = data_manager.get_semester()
    # Adicionar: só disciplinas do semestre ativo. Remover: qualquer disciplina conhecida
    # (para ainda se poderem limpar eventos de um semestre anterior).
    valid = SUBJECTS if tipo == "remove" else subjects_for_semester(semester)
    if subject not in valid:
        await interaction.response.send_message(
            f"⚠️ Disciplina inválida. Escolhe uma das sugestões do {semester}º semestre.",
            ephemeral=True,
        )
        return

    channel_id = data_manager.get_calendar_channel_id()
    channel = interaction.guild.get_channel(channel_id) if channel_id else None
    if channel is None:
        await interaction.response.send_message(
            "⚠️ O canal do calendário ainda não está configurado. "
            "Um Manager tem de usar `/configcalendario` primeiro.",
            ephemeral=True,
        )
        return

    label = CALENDAR_KINDS[o_que]
    desc = f"{label} de **{subject_label(subject)}** em **{date.strftime('%d/%m/%Y')}**"
    if tipo == "add":
        ok = data_manager.add_calendar_event(o_que, subject, date.isoformat())
        if not ok:
            await interaction.response.send_message(
                f"⚠️ Esse evento já existe: {desc}.", ephemeral=True
            )
            return
        action, title, color = "calendario_add", "📅 Novo evento", discord.Color.green()
    else:
        ok = data_manager.remove_calendar_event(o_que, subject, date.isoformat())
        if not ok:
            await interaction.response.send_message(
                f"⚠️ Não encontrei esse evento: {desc}.", ephemeral=True
            )
            return
        action, title, color = "calendario_remove", "🗑️ Evento removido", discord.Color.red()

    data_manager.add_log(
        str(interaction.user.id), get_user_role(interaction),
        action, None, f"{o_que} | {subject} | {date.isoformat()}"
    )

    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="Tipo", value=label, inline=True)
    embed.add_field(name="Disciplina", value=subject_label(subject), inline=True)
    embed.add_field(name="Data", value=date.strftime("%d/%m/%Y"), inline=True)
    embed.set_footer(text=f"Por {interaction.user.display_name}")
    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        await interaction.response.send_message(
            f"⚠️ O evento foi guardado, mas não consegui enviar a mensagem para {channel.mention}.",
            ephemeral=True,
        )
        return
    await interaction.response.send_message(
        f"✅ Feito. Mensagem enviada para {channel.mention}.", ephemeral=True
    )


@calendario.autocomplete("disciplina")
async def calendario_disciplina_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    """Sugere as disciplinas do semestre ativo (por nome)."""
    term = current.strip().lower()
    subjects = subjects_for_semester(data_manager.get_semester())
    return [
        app_commands.Choice(name=subject_label(code)[:100], value=code)
        for code, name in subjects.items()
        if term in name.lower()
    ][:25]


@bot.tree.command(
    name="configsemestre",
    description="Define o semestre ativo do calendário (1 ou 2). (Apenas Managers)",
    guild=guild_obj,
)
@app_commands.describe(qual="Semestre cujas disciplinas aparecem no /calendario")
@app_commands.choices(qual=[
    app_commands.Choice(name="1", value=1),
    app_commands.Choice(name="2", value=2),
])
async def configsemestre(interaction: discord.Interaction, qual: int):
    if not user_is_manager(interaction):
        await interaction.response.send_message(
            "❌ Apenas os **Managers** podem usar este comando.", ephemeral=True
        )
        return

    data_manager.set_semester(qual)
    data_manager.add_log(
        str(interaction.user.id), get_user_role(interaction),
        "configsemestre", None, f"Definiu semestre ativo: {qual}"
    )
    await interaction.response.send_message(
        f"✅ Semestre ativo definido para o **{qual}º semestre**."
    )


@bot.tree.command(
    name="configcalendario",
    description="Define o canal onde o bot publica os eventos do calendário. (Apenas Managers)",
    guild=guild_obj,
)
@app_commands.describe(canal="Canal onde os eventos do calendário serão publicados")
async def configcalendario(interaction: discord.Interaction, canal: discord.TextChannel):
    if not user_is_manager(interaction):
        await interaction.response.send_message(
            "❌ Apenas os **Managers** podem usar este comando.", ephemeral=True
        )
        return

    data_manager.set_calendar_channel_id(canal.id)
    data_manager.add_log(
        str(interaction.user.id), get_user_role(interaction),
        "configcalendario", None, f"Definiu canal do calendário: {canal.id}"
    )
    await interaction.response.send_message(
        f"✅ Canal do calendário configurado para {canal.mention}."
    )


# ─────────────────────────────────────────────────────────────
# Arranque do Bot
# ─────────────────────────────────────────────────────────────



if __name__ == "__main__":
    bot.run(config.get_token())
