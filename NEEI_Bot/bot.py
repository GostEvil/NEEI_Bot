import discord
from discord import app_commands
from discord.ext import commands

import config
import data_manager


# ─────────────────────────────────────────────────────────────
# Setup do Bot
# ─────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True  # Necessário para gerir membros e roles

bot = commands.Bot(command_prefix="!", intents=intents)
guild_obj = discord.Object(id=config.get_guild_id())


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
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos: {e}")


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


# ─────────────────────────────────────────────────────────────
# Comandos: Listagens (/listadmin e /listneei)
# ─────────────────────────────────────────────────────────────

@bot.tree.command(
    name="listadmin",
    description="Mostra todos os Admins e Managers do bot. (Apenas Admins/Managers)",
    guild=guild_obj,
)
async def listadmin(interaction: discord.Interaction):
    # 1. Verificar permissão
    if not user_is_admin_or_manager(interaction):
        await interaction.response.send_message(
            "❌ Não tens permissão para usar este comando.",
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
    description="Mostra todos os membros com a role NEEI. (Apenas Admins/Managers)",
    guild=guild_obj,
)
async def listneei(interaction: discord.Interaction):
    # 1. Verificar permissão
    if not user_is_admin_or_manager(interaction):
        await interaction.response.send_message(
            "❌ Não tens permissão para usar este comando.",
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


# ─────────────────────────────────────────────────────────────
# Arranque do Bot
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bot.run(config.get_token())
