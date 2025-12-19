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
#intents.message_content = True 
intents.reactions = True   

bot = commands.Bot(command_prefix='$', intents=intents)

#stores bags and their itemsL {'bag_name':[list of items]}
bags = {} 

# Stores active sessions: { message_id: [list_of_remaining_items] }
active_sessions = {}

# Tracks which bag is running on which message: { 'bag_name': message_id }
bag_tracker = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("-------------------------")

# --- COMMANDS ---

@bot.command(name='create')
async def create_bag(ctx, bag_name: str):
    """
    Usage: $create bagname
    Example: $create apple
    """
    if bag_name in bags:
        await ctx.send(f"A bag named '{bag_name}' already exists!")
    else:
        bags[bag_name] = []
        await ctx.send(f"Created a new empty bag named: **{bag_name}**")

@bot.command(name='delete')
async def delete_bag(ctx, bag_name: str):
    """
    Usage: $delete bagname
    Example: $delete apple
    """

    if bag_name not in bags:
        await ctx.send(f"A bag named '{bag_name}' does not exist!")
    elif bag_name in bags and bag_name in bag_tracker:
        await ctx.send(f"A bag named '{bag_name}' is currently active. Use `$end {bag_name}` first.")
    else:
        del bags[bag_name] 
        await ctx.send(f"Deleted: **{bag_name}**")

@bot.command(name='showallbags')
async def show_all_bags(ctx):
    """
    Usage: $showallbags
    Example: $showallbags
    """

    if len(bags)==0:
        await ctx.send(f"There are not yet any bags use `$create 'bag_name'` to create a bag.")
    
    else:
        bag_name_list = list(bags.keys())
        bag_name_string = '\n- '.join(bag_name_list)

        await ctx.send(f"There are **{len(bags)}** total bags.\n **Current Bags:**\n- {bag_name_string}")




@bot.command(name='add')
async def add_to_bag(ctx, bag_name: str, *, content: str):
    """
    Usage: $add bagname item1, item2, item3
    Example: $add apple red, green, blue, red and yellow, white
    """
    if bag_name not in bags:
        await ctx.send(f"Bag '{bag_name}' does not exist. Create it first!")
        return
    
    # 1. Split the content string by commas
    # 2. .strip() removes the leading/trailing spaces (e.g. " green" -> "green")
    # 3. 'if item.strip()' ensures we don't add empty items if there are double commas
    new_items = [item.strip() for item in content.split(',') if item.strip()]
    
    if not new_items:
        await ctx.send("I couldn't find any items to add. Make sure to separate them with commas!")
        return

    bags[bag_name].extend(new_items)
    await ctx.send(f"✅ Added {len(new_items)} items to **{bag_name}**. Total items: {len(bags[bag_name])}")

@bot.command(name='remove')
async def remove_from_bag(ctx, bag_name: str, *, content: str):
    """
    Usage: $remove bagname item1 item2 ...
    Example: $remove apple green
    """
    if bag_name not in bags:
        await ctx.send(f"Bag '{bag_name}' does not exist.")
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
        if item in bags[bag_name]:
            bags[bag_name].remove(item)
            removed_count += 1
            
    await ctx.send(f"❌ Removed {removed_count} items from **{bag_name}**.")

@bot.command(name='drop')
async def drop_item(ctx, bag_name: str, index: int):
    """
    Drops an item based on zero-based indexing.
    Usage: $drop bagname 0
    Example: $drop apple 0 (removes the very first item)
    """
    if bag_name not in bags:
        await ctx.send(f"Bag '{bag_name}' does not exist.")
        return
    
    bag = bags[bag_name]
    
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
    if bag_name in bags and len(bags[bag_name])>=1:
        content = ", ".join(bags[bag_name])
        await ctx.send(f"**{bag_name}** contains: {content}")
    elif bag_name in bags and len(bags[bag_name])==0:
        await ctx.send(f"'{bag_name}' is empty.")
    else:
        await ctx.send(f"'{bag_name}' not found.")

@bot.command(name='start')
async def start_session(ctx, bag_name: str):
    """
    Starts a blind bag session.

    Usage: $start bagname
    Example: $start apple
    """
    if bag_name not in bags or len(bags[bag_name]) == 0:
        await ctx.send(f"Bag '{bag_name}' does not exist or is empty!")
        return

    # NEW CHECK: Prevent starting a session if one is already running for this bag
    if bag_name in bag_tracker:
        await ctx.send(f"A session for **{bag_name}** is already running! Use `$end {bag_name}` first.")
        return

    # Create a COPY of the items (this ensures the original bag stays safe)
    session_items = bags[bag_name].copy()
    random.shuffle(session_items)

    msg = await ctx.send(f"**BLIND BAG SESSION STARTED: {bag_name}**\nReact with 👜 to grab an item! ({len(session_items)} items left)")
    await msg.add_reaction("👜")

    # Save to active_sessions (for reactions) AND bag_tracker (for the end command)
    active_sessions[msg.id] = session_items
    bag_tracker[bag_name] = msg.id

@bot.command(name='end')
async def end_session(ctx, bag_name: str):
    """
    Ends a blind bag session.

    Usage: $end bagname
    Example: $end apple
    """
    # Check if the bag is actually currently running a session
    if bag_name not in bag_tracker:
        await ctx.send(f"There is no active session for bag '{bag_name}'.")
        return

    # 1. Find the Message ID associated with this bag
    msg_id = bag_tracker[bag_name]

    # 2. Remove the session data from memory
    if msg_id in active_sessions:
        del active_sessions[msg_id]
    
    # 3. Remove the lock from the tracker
    del bag_tracker[bag_name]

    await ctx.send(f"Session for **{bag_name}** has ended. The bag has been returned to its original state.")



@bot.event
async def on_raw_reaction_add(payload):
    # 1. Ignore the bot's own reactions
    if payload.user_id == bot.user.id:
        return

    # 2. Check if the message is an active session
    if payload.message_id in active_sessions:
        bag_name = list(bag_tracker.keys())[list(bag_tracker.values()).index(payload.message_id)]
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = payload.member 
        
        # --- AUTO-REMOVE REACTION ---
        if user:
            try:
                await message.remove_reaction(payload.emoji, user)
            except:
                pass

        # 3. Handle the Item Pull
        current_items = active_sessions[payload.message_id]

        if len(current_items) > 0:
            item = current_items.pop(0)
            
            # --- NEW: SEND DIRECT MESSAGE ---
            try:
                await user.send(f"👜 You pulled: **{item}** from the bag!")
            except discord.Forbidden:
                # If the user has DMs blocked, notify them in the channel
                await channel.send(f"{user.mention}, I couldn't DM you! Please open your DMs to receive your item.", delete_after=10)
            
            # Update the count in the public message
            new_count = len(current_items)
            await message.edit(content=f"**BLIND BAG SESSION ACTIVE: {bag_name}**\nReact with 👜 to grab an item! ({new_count} items left)")
            
            # If the bag becomes empty exactly now, notify the channel
            if new_count == 0:
                await message.edit(content=f"**BLIND BAG SESSION ACTIVE: {bag_name}** The bag is now empty! Use `$end` to close the session.")
        else:
            try:
                await user.send("The bag is empty!")
            except:
                pass

webserver.keep_alive()
bot.run(TOKEN)