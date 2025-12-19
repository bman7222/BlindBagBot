import discord
import random
import os 
import webserver
from discord.ext import commands

import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True 
intents.reactions = True   

bot = commands.Bot(command_prefix='$', intents=intents)

# --- SERVER-EXCLUSIVE STORAGE ---
# Structure: { guild_id: { bag_name: [items] } }
bags = {} 

# Structure: { message_id: {"items": [], "guild_id": 0, "bag_name": ""} }
active_sessions = {}

# Structure: { guild_id: { bag_name: message_id } }
bag_tracker = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("-------------------------")

# Helper to ensure guild exists in storage
def ensure_guild(guild_id):
    if guild_id not in bags:
        bags[guild_id] = {}
    if guild_id not in bag_tracker:
        bag_tracker[guild_id] = {}

# --- COMMANDS ---

@bot.command(name='create')
async def create_bag(ctx, bag_name: str):
    """
    Usage: $create bagname
    Example: $create apple
    """
    ensure_guild(ctx.guild.id)
    server_bags = bags[ctx.guild.id]
    
    if bag_name in server_bags:
        await ctx.send(f"A bag named '{bag_name}' already exists in this server!")
    else:
        server_bags[bag_name] = []
        await ctx.send(f"Created a new empty bag named: **{bag_name}**")

@bot.command(name='delete')
async def delete_bag(ctx, bag_name: str):
    """
    Usage: $delete bagname
    Example: $delete apple
    """
    ensure_guild(ctx.guild.id)
    server_bags = bags[ctx.guild.id]
    server_tracker = bag_tracker[ctx.guild.id]

    if bag_name not in server_bags:
        await ctx.send(f"A bag named '{bag_name}' does not exist in this server!")
    elif bag_name in server_tracker:
        await ctx.send(f"A bag named '{bag_name}' is currently active. Use `$end {bag_name}` first.")
    else:
        del server_bags[bag_name] 
        await ctx.send(f"Deleted: **{bag_name}**")

@bot.command(name='showallbags')
async def show_all_bags(ctx):
    """
    Usage: $showallbags
    Example: $showallbags
    """
    ensure_guild(ctx.guild.id)
    server_bags = bags[ctx.guild.id]

    if not server_bags:
        await ctx.send(f"There are no bags in this server yet. Use `$create 'bag_name'` to make one.")
    else:
        bag_name_list = list(server_bags.keys())
        bag_name_string = '\n- '.join(bag_name_list)
        await ctx.send(f"**Current Bags in this Server:**\n- {bag_name_string}")

@bot.command(name='add')
async def add_to_bag(ctx, bag_name: str, *, content: str):
    """
    Usage: $add bagname item1, item2, item3
    Example: $add apple red, green, blue
    """
    ensure_guild(ctx.guild.id)
    server_bags = bags[ctx.guild.id]
    server_tracker = bag_tracker[ctx.guild.id]

    if bag_name not in server_bags:
        await ctx.send(f"Bag '{bag_name}' does not exist in server. Create it first!")
        return
    
    if bag_name in server_tracker:
        await ctx.send(f"A bag named '{bag_name}' is currently active. Use `$end {bag_name}` first.")
        return 

    # Split and clean the input items
    new_items = [item.strip() for item in content.split(',') if item.strip()]
    if not new_items:
        await ctx.send("I couldn't find any items to add. Make sure to separate them with commas!")
        return

    added_count = 0
    current_bag_items = server_bags[bag_name] 
    for item in new_items:
        if item in current_bag_items:
            await ctx.send(f"item {item} is already in the bag")
        else:
            current_bag_items.append(item)
            added_count += 1

    if added_count > 0:
        await ctx.send(f"✅ Added {added_count} new items to **{bag_name}**. Total items: {len(current_bag_items)}")
    else:
        await ctx.send("No new items were added.")

@bot.command(name='remove')
async def remove_from_bag(ctx, bag_name: str, *, content: str):
    """
    Usage: $remove bagname item1 item2 ...
    Example: $remove apple green
    """
    ensure_guild(ctx.guild.id)
    server_bags = bags[ctx.guild.id]
    server_tracker = bag_tracker[ctx.guild.id]

    if bag_name not in server_bags:
        await ctx.send(f"Bag '{bag_name}' does not exist.")
        return
    
    if bag_name in server_tracker:
        await ctx.send(f"A bag named '{bag_name}' is currently active. Use `$end {bag_name}` first.")
        return
    
    # 1. Split the content string by commas
    # 2. .strip() removes the leading/trailing spaces (e.g. " green" -> "green")
    # 3. 'if item.strip()' ensures we don't add empty items if there are double commas
    new_items = [item.strip() for item in content.split(',') if item.strip()]
    
    if not new_items:
        await ctx.send("I couldn't find any items to add. Make sure to separate them with commas!")
        return
    
    removed_count = 0
    for item in new_items:
        if item in server_bags[bag_name]:
            server_bags[bag_name].remove(item)
            removed_count += 1
            
    await ctx.send(f"❌ Removed {removed_count} items from **{bag_name}**.")

@bot.command(name='drop')
async def drop_item(ctx, bag_name: str, index: int):
    """
    Drops an item based on zero-based indexing.
    Usage: $drop bagname 0
    Example: $drop apple 0 (removes the very first item)
    """
    ensure_guild(ctx.guild.id)
    server_bags = bags[ctx.guild.id]
    server_tracker = bag_tracker[ctx.guild.id]

    if bag_name not in server_bags:
        await ctx.send(f"Bag '{bag_name}' does not exist.")
        return
    
    if bag_name in server_tracker:
        await ctx.send(f"A bag named '{bag_name}' is currently active. Use `$end {bag_name}` first.")
        return
    
    bag = server_bags[bag_name]
    
    # Check if the bag is empty
    if not bag:
        await ctx.send(f"The bag '{bag_name}' is currently empty.")
        return

    # Check if the index is within the valid range
    if 0 <= index < len(bag):
        # .pop(index) removes and returns the item at that specific position
        removed_item = bag.pop(index)
        await ctx.send(f"Successfully dropped item at index `{index}`: **{removed_item}** from **{bag_name}**.")
    else:
        await ctx.send(f"Invalid index! **{bag_name}** has indices `0` through `{len(bag) - 1}`. Please try again.")

@bot.command(name='check')
async def check_bag(ctx, bag_name: str):
    """
    See what is inside a bag.
    """
    ensure_guild(ctx.guild.id)
    server_bags = bags[ctx.guild.id]
    
    if bag_name in server_bags:
        items = server_bags[bag_name]
        if items:
            await ctx.send(f"**{bag_name}** contains: {', '.join(items)}")
        else:
            await ctx.send(f"'{bag_name}' is empty.")
    else:
        await ctx.send("Bag not found.")
        
@bot.command(name='start')
async def start_session(ctx, bag_name: str):
    ensure_guild(ctx.guild.id)
    server_bags = bags[ctx.guild.id]
    server_tracker = bag_tracker[ctx.guild.id]

    if bag_name not in server_bags or not server_bags[bag_name]:
        await ctx.send("Bag is empty or doesn't exist!")
        return

    if bag_name in server_tracker:
        await ctx.send(f"Session for **{bag_name}** is already running!")
        return

    session_items = server_bags[bag_name].copy()
    random.shuffle(session_items)

    msg = await ctx.send(f"**BLIND BAG SESSION STARTED: {bag_name}**\nReact with 👜 to grab an item! ({len(session_items)} items left)")
    await msg.add_reaction("👜")

    # Store guild context so the reaction handler knows which server/bag this message belongs to
    active_sessions[msg.id] = {
        "items": session_items,
        "guild_id": ctx.guild.id,
        "bag_name": bag_name
    }
    server_tracker[bag_name] = msg.id

@bot.command(name='end')
async def end_session(ctx, bag_name: str):
    ensure_guild(ctx.guild.id)
    server_tracker = bag_tracker[ctx.guild.id]

    if bag_name not in server_tracker:
        await ctx.send(f"No active session for '{bag_name}'.")
        return

    msg_id = server_tracker[bag_name]
    if msg_id in active_sessions:
        del active_sessions[msg_id]
    
    del server_tracker[bag_name]
    await ctx.send(f"Session for **{bag_name}** has ended.")



@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    if payload.message_id in active_sessions:
        session_data = active_sessions[payload.message_id]
        guild_id = session_data["guild_id"]
        bag_name = session_data["bag_name"]

        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = payload.member
        
        # --- AUTO-REMOVE REACTION ---
        if user:
            try: await message.remove_reaction(payload.emoji, user)
            except: pass

        current_items = session_data["items"]

        if len(current_items) > 0:
            item = current_items.pop(0)
            
            #send DM
            try:
                await user.send(f"👜 You pulled: **{item}** from the bag!")
            except discord.Forbidden:
                # If the user has DMs blocked, notify them in the channel
                await channel.send(f"{user.mention}, I couldn't DM you! Please open your DMs to receive your item.", delete_after=10)
            
            # Update the count in the public message
            new_count = len(current_items)
            if new_count == 0:
                await message.edit(content=f"**SESSION EMPTY: {bag_name}**\nAll items have been claimed! Use `$end`.")
            else:
                await message.edit(content=f"**BLIND BAG SESSION ACTIVE: {bag_name}**\nReact with 👜 to grab an item! ({new_count} items left)")
            
        else:
            try: await user.send("The bag is empty!")
            except: pass

webserver.keep_alive()
bot.run(TOKEN)