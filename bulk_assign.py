# -*- coding: utf-8 -*-
"""
Script de atribuicao em massa da role NEEI.
Procura cada membro no servidor pelo numero mecanografico
(presente no display name no formato "Nome (aXXXXX)")
e atribui automaticamente a role NEEI.

Uso: python bulk_assign.py
"""

import asyncio
import re
import sys
import io

# Forcar output UTF-8 no Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import discord
from dotenv import load_dotenv
import config

# ─────────────────────────────────────────────────────────────
# Lista de numeros mecanograficos a receber o cargo NEEI
# ─────────────────────────────────────────────────────────────

NEEI_MEMBERS = [
    "a64716",  # Joao Pedro Esteves Caldas          (Mesa - Presidente)
    "a59445",  # Carolina Garcia Fernandes           (Mesa - 1o Secretario)
    "a63426",  # Nuno Jose Freitas da Silva          (Mesa - 2o Secretario)
    "a54457",  # Daniel Filipe Campos Coelho         (Direcao - Presidente)
    "a50765",  # Luis Carlos Miranda Fernandes       (Direcao - Vice-Presidente)
    "a60862",  # Vitor Hugo da Silva Monteiro        (Direcao - Tesoureiro)
    "a63416",  # Joana dos Santos Moreira            (Direcao - 1o Secretario)
    "a60325",  # Artur Goncalo Teixeira Pinheiro     (Direcao - 2o Secretario)
    "a60838",  # Ines Freitas                        (Direcao - 1o Vogal)
    "a68015",  # Lara Sebastiao Lopes                (Direcao - 2o Vogal)
    "a67357",  # Joao Andre Pereira Rodrigues        (Direcao - 3o Vogal)
    "a59451",  # Goncalo Filipe Pedrosa Pereira      (Direcao - 4o Vogal)
    "a64725",  # Tiago David Goncalves Tomas         (Direcao - 5o Vogal)
    "a56547",  # Carlos Miguel Gomes Moreira         (Direcao - 6o Vogal)
    "a60556",  # Francisco Jose da Silva Morais      (Conselho Fiscal - Presidente)
    "a55726",  # Diogo Jose Teixeira de Sousa        (Conselho Fiscal - Vice-Presidente)
    "a60850",  # Pedro Miguel Coelho Ribeiro         (Conselho Fiscal - Relator)
]


# ─────────────────────────────────────────────────────────────
# Logica principal (sem bot, usa HTTPClient direto)
# ─────────────────────────────────────────────────────────────

async def main():
    load_dotenv()
    token     = config.get_token()
    guild_id  = config.get_guild_id()
    role_name = config.get_neei_role_name()

    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents=intents)

    await client.login(token)

    # Buscar o guild diretamente via HTTP (sem precisar de on_ready)
    guild = await client.fetch_guild(guild_id)
    print(f"\n[OK] Guild encontrada: {guild.name}")

    # Buscar a role NEEI
    roles = await guild.fetch_roles()
    role  = discord.utils.get(roles, name=role_name)
    if role is None:
        print(f"[ERRO] Cargo '{role_name}' nao encontrado.")
        await client.close()
        return

    print(f"[ALVO] Cargo: {role.name} (ID: {role.id})")

    # Buscar TODOS os membros do servidor via HTTP
    print("[...] A carregar todos os membros do servidor...")
    all_members = []
    async for member in guild.fetch_members(limit=None):
        all_members.append(member)
    print(f"[OK] {len(all_members)} membros carregados.\n")
    print("=" * 55)
    print(f"[INFO] A processar {len(NEEI_MEMBERS)} numeros mecanograficos...")
    print("=" * 55)

    found     = []
    not_found = []
    skipped   = []

    for num in NEEI_MEMBERS:
        # O display name usa apenas o numero sem o "a" -> ex: "Nome (64716)"
        num_digits = num.lstrip("aA")  # Remove o prefixo "a" -> "64716"
        pattern = re.compile(re.escape(num_digits), re.IGNORECASE)

        match = None
        for m in all_members:
            if pattern.search(m.display_name) or pattern.search(m.name):
                match = m
                break

        if match is None:
            not_found.append(num)
            print(f"  [NAO ENCONTRADO] {num}")
            continue

        # Verificar se ja tem a role (roles do member via fetch)
        member_roles_ids = [r.id for r in match.roles]
        if role.id in member_roles_ids:
            skipped.append((num, match.display_name))
            print(f"  [JA TEM CARGO]   {match.display_name} ({num})")
            continue

        try:
            await match.add_roles(role, reason="Atribuicao em massa via bulk_assign.py")
            found.append((num, match.display_name))
            print(f"  [ATRIBUIDO]      {match.display_name} ({num})")
        except discord.Forbidden:
            print(f"  [SEM PERMISSAO]  {match.display_name} ({num})")
        except discord.HTTPException as e:
            print(f"  [ERRO HTTP]      {match.display_name} ({num}) -- {e}")

        await asyncio.sleep(0.5)

    # Resumo final
    print("\n" + "=" * 55)
    print("RESUMO FINAL")
    print("=" * 55)
    print(f"  Cargo atribuido  : {len(found)}")
    print(f"  Ja tinham o cargo: {len(skipped)}")
    print(f"  Nao encontrados  : {len(not_found)}")

    if not_found:
        print("\n  Numeros nao encontrados no servidor:")
        for num in not_found:
            print(f"    - {num}")

    print("\n[CONCLUIDO]\n")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
