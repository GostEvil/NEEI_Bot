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


def user_has_neei_role(interaction: discord.Interaction) -> bool:
    """Verifica se o utilizador tem o cargo NEEI no servidor."""
    role_name = config.get_neei_role_name()
    return any(role.name == role_name for role in interaction.user.roles)


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
    image_file = await imagem.to_file()

    # 5. Enviar apenas a imagem no canal de destino
    await target_channel.send(file=image_file)

    # 6. Responder de forma privada (ephemeral) confirmando o envio
    await interaction.response.send_message(
        f"✅ Imagem enviada com sucesso no canal {target_channel.mention}!",
        ephemeral=True,
    )



# ─────────────────────────────────────────────────────────────
# Arranque do Bot
# ─────────────────────────────────────────────────────────────



if __name__ == "__main__":
    bot.run(config.get_token())
