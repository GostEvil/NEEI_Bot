"""
Script de atribuição em massa da role NEEI.
Procura cada membro no servidor pelo número mecanográfico
(presente no display name no formato "Nome (aXXXXX)")
e atribui automaticamente a role NEEI.

Uso: python bulk_assign.py
"""

import asyncio
import re
import discord
from dotenv import load_dotenv
import config

# ─────────────────────────────────────────────────────────────
# Lista de números mecanográficos a receber o cargo NEEI
# ─────────────────────────────────────────────────────────────

NEEI_MEMBERS = [
    "a64716",  # João Pedro Esteves Caldas         (Mesa Assembleia - Presidente)
    "a59445",  # Carolina Garcia Fernandes          (Mesa Assembleia - 1º Secretário)
    "a63426",  # Nuno José Freitas da Silva         (Mesa Assembleia - 2º Secretário)
    "a54457",  # Daniel Filipe Campos Coelho        (Direção - Presidente)
    "a50765",  # Luís Carlos Miranda Fernandes      (Direção - Vice-Presidente)
    "a60862",  # Vítor Hugo da Silva Monteiro       (Direção - Tesoureiro)
    "a63416",  # Joana dos Santos Moreira           (Direção - 1º Secretário)
    "a60325",  # Artur Gonçalo Teixeira Pinheiro    (Direção - 2º Secretário)
    "a60838",  # Inês Freitas                       (Direção - 1º Vogal)
    "a68015",  # Lara Sebastião Lopes               (Direção - 2º Vogal)
    "a67357",  # João André Pereira Rodrigues       (Direção - 3º Vogal)
    "a59451",  # Gonçalo Filipe Pedrosa Pereira     (Direção - 4º Vogal)
    "a64725",  # Tiago David Gonçalves Tomás        (Direção - 5º Vogal)
    "a56547",  # Carlos Miguel Gomes Moreira        (Direção - 6º Vogal)
    "a60556",  # Francisco José da Silva Morais     (Conselho Fiscal - Presidente)
    "a55726",  # Diogo José Teixeira de Sousa       (Conselho Fiscal - Vice-Presidente)
    "a60850",  # Pedro Miguel Coelho Ribeiro        (Conselho Fiscal - Relator)
]


# ─────────────────────────────────────────────────────────────
# Lógica do script
# ─────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"\n✅ Ligado como {client.user}")
    print("=" * 55)

    guild = client.get_guild(config.get_guild_id())
    if guild is None:
        print("❌ Servidor não encontrado. Verifica o GUILD_ID no .env")
        await client.close()
        return

    # Forçar o carregamento de TODOS os membros do servidor para a cache
    print("⏳ A carregar membros do servidor...")
    await guild.chunk()
    print(f"✅ {guild.member_count} membros carregados.\n")

    # Obter a role NEEI
    role_name = config.get_neei_role_name()
    role = discord.utils.get(guild.roles, name=role_name)
    if role is None:
        print(f"❌ Cargo '{role_name}' não encontrado no servidor.")
        await client.close()
        return

    print(f"🎯 Cargo alvo: {role.name}")
    print(f"👥 Total de membros a processar: {len(NEEI_MEMBERS)}\n")

    found     = []
    not_found = []
    skipped   = []

    # Processar cada número mecanográfico
    for num in NEEI_MEMBERS:
        # Procura por (aXXXXX) no display name ou username do membro
        pattern = re.compile(re.escape(num), re.IGNORECASE)
        match = discord.utils.find(
            lambda m: pattern.search(m.display_name) or pattern.search(m.name),
            guild.members,
        )

        if match is None:
            not_found.append(num)
            print(f"  ⚠️  Não encontrado: {num}")
            continue

        if role in match.roles:
            skipped.append((num, match.display_name))
            print(f"  ⏭️  Já tem o cargo : {match.display_name} ({num})")
            continue

        try:
            await match.add_roles(role, reason="Atribuição em massa via bulk_assign.py")
            found.append((num, match.display_name))
            print(f"  ✅ Cargo atribuído: {match.display_name} ({num})")
        except discord.Forbidden:
            print(f"  ❌ Sem permissão  : {match.display_name} ({num})")
        except discord.HTTPException as e:
            print(f"  ❌ Erro HTTP      : {match.display_name} ({num}) — {e}")

        # Pequena pausa para não exceder o rate limit da API do Discord
        await asyncio.sleep(0.5)

    # Resumo final
    print("\n" + "=" * 55)
    print("📊 RESUMO")
    print("=" * 55)
    print(f"  ✅ Cargo atribuído : {len(found)}")
    print(f"  ⏭️  Já tinham o cargo: {len(skipped)}")
    print(f"  ⚠️  Não encontrados : {len(not_found)}")

    if not_found:
        print("\n  Números mecanográficos não encontrados no servidor:")
        for num in not_found:
            print(f"    - {num}")

    print("\n✔️  Script concluído!\n")
    await client.close()


if __name__ == "__main__":
    load_dotenv()
    client.run(config.get_token())
