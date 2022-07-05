import datetime
import os
import discord
from discord.ext import commands
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests
import random
import re
import math

uri = os.environment.get('URI')
token = os.environment.get('BOT_TOKEN')

cluster = MongoClient(uri)
db = cluster['discord-bot']
pokemon = db['pokemon']
servers = db['servers']

pokemon.create_index("createdAt", expireAfterSeconds=1000, partialFilterExpression={"owner": ""})

intents = discord.Intents().all()

client = commands.Bot(command_prefix="p!", intents=intents)



@client.event
async def on_guild_join(guild):
    res = servers.find_one({"_id": guild.id})
    if res is None:
        # print(guild)
        servers.insert_one(
            {"_id": guild.id, "spawn_count": 10, "spawn_channel": guild.text_channels[0].id, "message_counter": 0})

        text_channel = guild.text_channels[0]
        embed = discord.Embed(
            title="welcome to Pokebot!",
            description="ThankYou for adding pokeBot to your server, Before you can start catching pokemon,"
                        "have a server admin run the command p!spawn and p!channel to set the pokemon spawn"
                        " count and spawn channel respectively",
            color=discord.Color.gold()
        )
        # embed.set_thumbnail("https://assets.pokemon.com/assets/cms2/img/pokedex/full/025.png")
        embed.set_author(name="harsh raj")
        await text_channel.send(embed=embed)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    server = servers.find_one({"_id": message.guild.id})
    if server is None:
        servers.insert_one(
            {"_id": guild.id, "spawn_Count": 5, "spawn_channel": guild.text_channels[0].id, "message_counter": 0})
    else:
        # print(server)
        message_counter = server["message_counter"]
        spawn_count = server["spawn_count"]

        if message_counter + 1 >= spawn_count:
            r = requests.get(f"https://pokeapi.co/api/v2/pokemon/{random.randint(1, 898)}")
            # print(r)
            data = r.json()
            # print(data)
            name = data["name"]
            image = data["sprites"]["other"]["official-artwork"]["front_default"]

            types = []

            for type in data["types"]:
                types.append(type["type"]['name'])

            hp = data["stats"][0]["base_stat"]

            attack = data["stats"][1]["base_stat"]

            defense = data["stats"][2]["base_stat"]

            special_attack = data["stats"][3]["base_stat"]

            special_defense = data["stats"][4]["base_stat"]

            speed = data["stats"][5]["base_stat"]

            weight = data["weight"]

            experience = data["base_experience"]

            abilities = []
            for ability in data["abilities"]:
                abilities.append(ability["ability"]["name"])

            level = 0

            new_pokemon = {
                "name": name, "image": image, "types": types, "hp": hp, "attack": attack, "defense": defense,
                "special_attack": special_attack, "special_defense": special_defense, "speed": speed,
                "weight": weight, "experience": experience, "abilities": abilities, "level": level, "owner": "",
                "selected": False, "spawn_server": message.guild.id, "createdAt": datetime.datetime.utcnow()
            }
            pokemon.insert_one(new_pokemon)

            embed = discord.Embed(
                title="A wild Pokemon has appeared!",
                description="Quick, Catch them with **p!catch pokemon_name**."
                            "Pokemon tend to run away 3 hours after they appear",
                color=discord.Color.gold()
            )
            embed.set_image(url=image)
            spawn_channel = message.guild.get_channel(server["spawn_channel"])
            await spawn_channel.send(embed=embed)
            message_counter = 0
        else:
            message_counter += 1

        servers.update_one(server, {"$set": {"message_counter": message_counter}})

        res = pokemon.find_one({"owner": message.author.id})

        if res is None:
            pass

        else:
            pokemon.update_one({"owner": message.author.id, "selected": True}, {"$inc": {"experience": 1}})

            poke = pokemon.find_one({"owner": message.author.id, "selected": True})

            exp = poke["experience"]

            level = poke["level"]

            if exp > math.pow(level, 3) and level < 100:
                pokemon.update_one(poke, {"$inc": {"level": 1}})

                await message.channel.send(f'{message.author.name} Pokemon {poke["name"]} has leveled up!')

    await client.process_commands(message)


@client.command()
@commands.is_owner()
async def spawn(ctx, count: int):
    servers.update_one({"_id": ctx.guild.id}, {"$set": {"spawn_count": count}})


@client.command()
@commands.is_owner()
async def channel(ctx, text_channel: discord.TextChannel):
    servers.update_one({"_id": ctx.guild.id}, {"$set": {"spawn_channel": text_channel.id}})


@client.command()
@commands.is_owner()
async def server(ctx):
    res = servers.find_one({"_id": ctx.guild.id})
    embed = discord.Embed(
        title=f'Server settings for {ctx.guild.name}',
        description=f'Spawn Count: {res["spawn_count"]}'
                    f'\nSpawnChannel: {ctx.guild.get_channel(res["spawn_channel"]).mention}',
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


@client.command()
async def inventory(ctx):
    inv = pokemon.find({'owner': ctx.author.id})
    inv = list(inv)
    if len(inv) > 0:
        items = ""
        embed = discord.Embed(
            title=f"{ctx.author.name}'s pokemon inventory",
            color=discord.Color.gold()
        )
        print(inv)
        for item in inv:
            print(item["name"])
            if item["selected"]:
                items = f'Name: {item["name"]} | Number: {item["_id"]}\n{items}'
            else:
                items += f'Name: {item["name"]} | Number: {item["_id"]}\n'
        embed.add_field(name="pokemon", value=items)
        await ctx.send(embed=embed)
    else:
        await ctx.send("you dont have pokemon in your inventory")


@client.command()
async def number(ctx, *, name: str):
    poke = pokemon.find({"owner": ctx.author.id, "name": name})
    poke = list(poke)
    if len(poke) > 0:
        items = ""
        embed = discord.Embed(
            title=f"{ctx.author.name}'s {name}",
            color=discord.Color.gold()
        )
        for item in poke:
            items += f'name: {item["name"]} | Number : {item["_id"]}\n'
        embed.add_field(name="pokemon", value="items")
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"you dont have pokemon with name {name}")


@client.command()
async def select(ctx, object_id: str):
    res = pokemon.find_one({"_id": ObjectId(object_id), "owner": ctx.author.id})
    if res is None:
        await ctx.send("You do not have a Pokemon with this Number in your inventory")
    else:
        pokemon.update_many({"owner": ctx.author.id, "selected": true}, {"$set": {"selected": False}})
        pokemon.update_one({"_id": ObjectId(object_id), "owner": ctx.author.id}, {"$set": {"selected": True}})
        await ctx.send(f"Name: {res['name']} | Number : {res['_id']} is now your selected pokemon")


@client.command()
async def info(ctx, object_id: str):
    poke = pokemon.find_one({"_id": ObjectId(object_id)})
    if poke is None:
        await ctx.send("A pokemon with this Number does not exist")
    else:
        stats = f'Level: {poke["level"]}\nExperience: {poke["experience"]}\nHP: {"hp"}\n' \
                f'Attack: {poke["attack"]}\nDefense: {poke["defense"]}\nSpecial Attack: {poke["special_attack"]}' \
                f'Special Defense: {poke["special_defense"]}\nSpeed: {poke["speed"]}\nWeight: {poke["weight"]}'
        abilities = ""
        for ability in poke["abilities"]:
            abilities += f'{ability}\n'

        types = ""
        for type in poke["types"]:
            abilities += f'{type}\n'

        embed = discord.Embed(
            title=f'Info and stats for {poke["name"]}',
            description=f'{poke["name"]} | {object_id}',
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=poke["image"])
        embed.add_field(name="stats", value=stats, inline=True)
        embed.add_field(name="Abilities", value=abilities, inline=True)
        embed.add_field(name="Types", value=types, inline=True)

        await ctx.send(embed=embed)


@client.command()
async def catch(ctx, *, name: str):
    # print("a")
    # print(ctx)
    poke = pokemon.find_one({"owner": "", "spawn_server": ctx.guild.id, "name": name.replace(" ", "-").lower()})

    if poke is None:

        await ctx.send("Either that is not the name of the Pokemon or this Pokemon has already been caught"
                       "or this Pokemon has run away")

    else:
        res = pokemon.find_one({"owner": ctx.author.id, "selected": True})

        if res is None:
            selected = True
        else:
            selected = False
        pokemon.update_one(poke, {"$set": {"owner": ctx.author.id, "selected": selected}})
        await ctx.send(f'{ctx.author.name} has caught a wild {poke["name"]}')


client.run(token)
