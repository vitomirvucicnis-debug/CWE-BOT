import os, random, sqlite3, time
import discord
from discord import app_commands
from discord.ext import commands

TOKEN=os.environ.get("DISCORD_TOKEN")
if not TOKEN: raise RuntimeError("DISCORD_TOKEN missing")
DB=sqlite3.connect(os.getenv("DATA_DIR",".")+"/cwe.sqlite3")
DB.execute("CREATE TABLE IF NOT EXISTS users (guild INTEGER,user INTEGER,coins INTEGER DEFAULT 0,xp INTEGER DEFAULT 0,last_daily INTEGER DEFAULT 0,PRIMARY KEY(guild,user))")
DB.execute("CREATE TABLE IF NOT EXISTS setup (guild INTEGER PRIMARY KEY,welcome INTEGER,levelup INTEGER,tickets INTEGER)")
DB.execute("CREATE TABLE IF NOT EXISTS member_roles (guild INTEGER PRIMARY KEY, role INTEGER NOT NULL, verify_channel INTEGER)")
DB.execute("CREATE TABLE IF NOT EXISTS channel_locks (guild INTEGER, channel INTEGER, role INTEGER, prior TEXT, PRIMARY KEY(guild,channel,role))")
DB.commit()
intents=discord.Intents.default()
intents.message_content=False
intents.members=False
bot=commands.Bot(command_prefix=commands.when_mentioned_or("?Cwe ","?cwe "),intents=intents,application_id=1561270741335285780)

def account(g,u):
 DB.execute("INSERT OR IGNORE INTO users(guild,user) VALUES (?,?)",(g,u));DB.commit()
 return DB.execute("SELECT coins,xp,last_daily FROM users WHERE guild=? AND user=?",(g,u)).fetchone()
def setting(g,key):
 row=DB.execute("SELECT "+key+" FROM setup WHERE guild=?",(g,)).fetchone()
 return row[0] if row else None
def set_setting(g,key,v):
 DB.execute("INSERT OR IGNORE INTO setup(guild) VALUES (?)",(g,))
 DB.execute("UPDATE setup SET "+key+"=? WHERE guild=?",(v,g));DB.commit()
def add(g,u,key,n):
 account(g,u);DB.execute("UPDATE users SET "+key+"="+key+"+? WHERE guild=? AND user=?",(n,g,u));DB.commit()

@bot.event
async def on_ready():
 # Rename the Discord bot account, then apply the same server nickname.
 if bot.user.name != "DRILL LIFE BOT":
  try:
   await bot.user.edit(username="DRILL LIFE BOT")
   print("BOT USERNAME UPDATED",bot.user.name,flush=True)
  except discord.HTTPException as e:
   print("BOT USERNAME UPDATE REJECTED",repr(e),flush=True)
 for guild in bot.guilds:
  try:
   member=guild.me
   if member and member.nick != "DRILL LIFE BOT":
    await member.edit(nick="DRILL LIFE BOT",reason="Requested bot rebrand")
    print("BOT NICKNAME UPDATED",guild.id,flush=True)
  except discord.HTTPException as e:
   print("BOT NICKNAME UPDATE REJECTED",guild.id,repr(e),flush=True)
 try:
  synced=await bot.tree.sync()
  print("READY",bot.user,"global commands",len(synced),flush=True)
  for guild in bot.guilds:
   try:
    bot.tree.copy_global_to(guild=guild)
    registered=await bot.tree.sync(guild=guild)
    print("GUILD SYNC",guild.id,len(registered),flush=True)
   except Exception as e:
    print("Guild sync failed",guild.id,repr(e),flush=True)
 except Exception as e: print("Sync error",repr(e),flush=True)

def make_welcome_embed(member):
 guild=member.guild
 count=guild.member_count
 joined=discord.utils.format_dt(member.joined_at or discord.utils.utcnow(),style="f")
 created=discord.utils.format_dt(member.created_at,style="R")
 embed=discord.Embed(title="🛡️ Welcome!",description=f"Welcome {member.mention} to **CWE clan**! You are member **#{count or '?'}**.\n\nPlease complete verification to unlock the community.",color=discord.Color.from_rgb(47,116,220))
 embed.add_field(name="Account created",value=created,inline=True)
 embed.add_field(name="Members",value=str(count or "?"),inline=True)
 embed.set_thumbnail(url=member.display_avatar.url)
 embed.set_footer(text=f"Member #{count or '?'} • {joined}")
 return embed

@bot.event
async def on_member_join(member):
 ch=member.guild.get_channel(setting(member.guild.id,"welcome") or 0)
 if ch:
  try: await ch.send(embed=make_welcome_embed(member))
  except discord.HTTPException as e:print("Welcome failed",repr(e),flush=True)

@bot.event
async def on_message(m):
 if m.author.bot or not m.guild:return
 old=account(m.guild.id,m.author.id)[1]; bonus=random.randint(5,12)
 add(m.guild.id,m.author.id,"xp",bonus)
 if (old+bonus)//100>old//100:
  ch=m.guild.get_channel(setting(m.guild.id,"levelup") or 0) or m.channel
  try: await ch.send(f"⭐ {m.author.mention} reached level {(old+bonus)//100}!")
  except discord.HTTPException: pass
 await bot.process_commands(m)

@bot.command(name="coins")
async def coins(ctx):
 balance=account(ctx.guild.id,ctx.author.id)[0]
 await ctx.send(f"🪙 {ctx.author.mention}, you have **{balance} Cwe Coins**!")

@bot.command(name="daily")
async def daily(ctx):
 g,u=ctx.guild.id,ctx.author.id; last=account(g,u)[2];now=int(time.time())
 if now-last<86400: return await ctx.send("⏰ You already claimed today's Cwe Coins.")
 DB.execute("UPDATE users SET coins=coins+100,last_daily=? WHERE guild=? AND user=?",(now,g,u));DB.commit()
 await ctx.send(f"🎁 {ctx.author.mention} claimed **100 Cwe Coins**!")

@bot.command(name="slot")
async def slot(ctx):
 items=["🍒","🍋","⭐","🍀","💎"];r=[random.choice(items) for _ in range(3)]
 win=25 if len(set(r))==1 else 0
 if win:add(ctx.guild.id,ctx.author.id,"coins",win)
 await ctx.send(" | ".join(r)+(" — 🎉 +25 Cwe Coins!" if win else " — Try again! (No cost)"))

@bot.command(name="leaderboard")
async def leaderboard(ctx):
 rows=DB.execute("SELECT user,coins FROM users WHERE guild=? ORDER BY coins DESC LIMIT 10",(ctx.guild.id,)).fetchall()
 await ctx.send("🏆 **Cwe Coins leaderboard**\n"+("\n".join(f"{i+1}. <@{u}> — {c}" for i,(u,c) in enumerate(rows)) or "No balances yet."))

@bot.tree.command(name="currency",description="How to earn Cwe Coins")
async def currency(i:discord.Interaction):
 await i.response.send_message("🪙 **Cwe Coins**: ?Cwe coins, ?Cwe daily, ?Cwe slot, ?Cwe leaderboard")

@bot.tree.command(name="lock",description="Lock a text channel for regular members")
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(i:discord.Interaction,channel:discord.TextChannel|None=None):
 ch=channel or i.channel
 await i.response.defer(ephemeral=True)
 if not ch.permissions_for(i.guild.me).manage_roles:
  return await i.followup.send("❌ CWE BOT needs Manage Roles permission to edit channel permissions.",ephemeral=True)
 roles=[i.guild.default_role]+[r for r in i.guild.roles if r!=i.guild.default_role and not r.permissions.administrator and not r.permissions.manage_channels and not r.permissions.manage_messages]
 changed=0
 for role in roles:
  overwrite=ch.overwrites_for(role)
  if overwrite.send_messages is False:continue
  prior="none" if overwrite.send_messages is None else "true"
  try:
   overwrite.send_messages=False
   await ch.set_permissions(role,overwrite=overwrite,reason="CWE channel lock")
   DB.execute("INSERT OR IGNORE INTO channel_locks(guild,channel,role,prior) VALUES (?,?,?,?)",(i.guild.id,ch.id,role.id,prior))
   changed+=1
  except discord.Forbidden:
   DB.commit();return await i.followup.send(f"❌ Missing permission to lock {ch.mention}. Check CWE BOT's Manage Roles and channel permission overrides.",ephemeral=True)
  except discord.HTTPException as e: print("Lock role error",role.id,repr(e),flush=True)
 DB.commit()
 await i.followup.send(f"🔒 Locked {ch.mention} for regular members ({changed} permission changes).",ephemeral=True)

@bot.tree.command(name="unlock",description="Restore channel permissions saved by /lock")
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(i:discord.Interaction,channel:discord.TextChannel|None=None):
 ch=channel or i.channel
 await i.response.defer(ephemeral=True)
 rows=DB.execute("SELECT role,prior FROM channel_locks WHERE guild=? AND channel=?",(i.guild.id,ch.id)).fetchall()
 if not rows:return await i.followup.send("ℹ️ No saved lock settings for this channel.",ephemeral=True)
 restored=0
 for roleid,prior in rows:
  role=i.guild.get_role(roleid)
  if role is None:continue
  overwrite=ch.overwrites_for(role)
  overwrite.send_messages=None if prior=="none" else True
  try:
   await ch.set_permissions(role,overwrite=overwrite,reason="CWE channel unlock")
   DB.execute("DELETE FROM channel_locks WHERE guild=? AND channel=? AND role=?",(i.guild.id,ch.id,roleid));restored+=1
  except discord.HTTPException as e:print("Unlock role error",roleid,repr(e),flush=True)
 DB.commit()
 await i.followup.send(f"🔓 Restored {restored} channel permissions in {ch.mention}.",ephemeral=True)

@bot.tree.command(name="welcome",description="Set welcome channel")
@app_commands.checks.has_permissions(manage_guild=True)
async def welcome(i:discord.Interaction,channel:discord.TextChannel):
 set_setting(i.guild.id,"welcome",channel.id)
 await i.response.send_message(f"✅ Welcome messages set to {channel.mention}",ephemeral=True)

@bot.tree.command(name="welcometest",description="Preview the CWE clan welcome card")
@app_commands.checks.has_permissions(manage_guild=True)
async def welcometest(i:discord.Interaction,channel:discord.TextChannel|None=None):
 ch=channel or i.guild.get_channel(setting(i.guild.id,"welcome") or 0) or i.channel
 try:
  await ch.send(embed=make_welcome_embed(i.user))
 except discord.Forbidden:
  return await i.response.send_message("❌ CWE BOT needs Send Messages and Embed Links in that channel.",ephemeral=True)
 await i.response.send_message(f"✅ Welcome test posted in {ch.mention}.",ephemeral=True)

@bot.tree.command(name="levelupsetup",description="Set level-up channel")
@app_commands.checks.has_permissions(manage_guild=True)
async def levelupsetup(i:discord.Interaction,channel:discord.TextChannel):
 set_setting(i.guild.id,"levelup",channel.id)
 await i.response.send_message(f"✅ Level-up messages set to {channel.mention}",ephemeral=True)

class OpenTicket(discord.ui.Button):
 def __init__(self):super().__init__(label="Open Ticket",style=discord.ButtonStyle.green,custom_id="cwe:open")
 async def callback(self,i:discord.Interaction):
  cat=i.guild.get_channel(setting(i.guild.id,"tickets") or 0)
  if not isinstance(cat,discord.CategoryChannel):return await i.response.send_message("Ticket system is not configured.",ephemeral=True)
  name=f"ticket-{i.user.id}"
  existing=discord.utils.get(cat.text_channels,name=name)
  if existing:return await i.response.send_message(f"Ticket already open: {existing.mention}",ephemeral=True)
  perms={i.guild.default_role:discord.PermissionOverwrite(view_channel=False),i.user:discord.PermissionOverwrite(view_channel=True,send_messages=True),i.guild.me:discord.PermissionOverwrite(view_channel=True,send_messages=True,manage_channels=True)}
  ch=await cat.create_text_channel(name,overwrites=perms)
  await ch.send(f"🎫 Ticket for {i.user.mention}.",view=CloseView())
  await i.response.send_message(f"✅ Opened {ch.mention}",ephemeral=True)

class CloseTicket(discord.ui.Button):
 def __init__(self):super().__init__(label="Close Ticket",style=discord.ButtonStyle.red,custom_id="cwe:close")
 async def callback(self,i:discord.Interaction):
  if not i.channel.name.startswith("ticket-"):return await i.response.send_message("Not a ticket channel.",ephemeral=True)
  owner=i.channel.name.removeprefix("ticket-")
  if str(i.user.id)!=owner and not i.user.guild_permissions.manage_channels:return await i.response.send_message("Only the ticket owner or moderators can close it.",ephemeral=True)
  await i.response.send_message("Closing ticket...",ephemeral=True)
  await i.channel.delete()

class OpenView(discord.ui.View):
 def __init__(self):super().__init__(timeout=None);self.add_item(OpenTicket())
class CloseView(discord.ui.View):
 def __init__(self):super().__init__(timeout=None);self.add_item(CloseTicket())

@bot.tree.command(name="ticketsetup",description="Create tickets and post a ticket panel")
@app_commands.checks.has_permissions(manage_channels=True)
async def ticketsetup(i:discord.Interaction,channel:discord.TextChannel):
 cat=discord.utils.get(i.guild.categories,name="Cwe Tickets")
 if not cat:cat=await i.guild.create_category("Cwe Tickets")
 set_setting(i.guild.id,"tickets",cat.id)
 await channel.send("🎫 **Cwe Support** — Press the button to open a ticket.",view=OpenView())
 await i.response.send_message(f"✅ Ticket panel posted in {channel.mention}",ephemeral=True)


@bot.tree.command(name="coins",description="Check your Cwe Coins balance")
async def slash_coins(i:discord.Interaction):
 await i.response.send_message(f"🪙 {i.user.mention}, you have **{account(i.guild.id,i.user.id)[0]} Cwe Coins**!")

@bot.tree.command(name="daily",description="Claim your daily Cwe Coins")
async def slash_daily(i:discord.Interaction):
 g,u=i.guild.id,i.user.id;last=account(g,u)[2];now=int(time.time())
 if now-last<86400:return await i.response.send_message("⏰ You already claimed today's Cwe Coins.",ephemeral=True)
 DB.execute("UPDATE users SET coins=coins+100,last_daily=? WHERE guild=? AND user=?",(now,g,u));DB.commit()
 await i.response.send_message(f"🎁 {i.user.mention} claimed **100 Cwe Coins**!")

@bot.tree.command(name="slot",description="Free Cwe Coins emoji slots")
async def slash_slot(i:discord.Interaction):
 items=["🍒","🍋","⭐","🍀","💎"];r=[random.choice(items) for _ in range(3)]
 win=25 if len(set(r))==1 else 0
 if win:add(i.guild.id,i.user.id,"coins",win)
 await i.response.send_message(" | ".join(r)+(" — 🎉 +25 Cwe Coins!" if win else " — Try again! (No cost)"))

@bot.tree.command(name="leaderboard",description="View the Cwe Coins leaderboard")
async def slash_leaderboard(i:discord.Interaction):
 rows=DB.execute("SELECT user,coins FROM users WHERE guild=? ORDER BY coins DESC LIMIT 10",(i.guild.id,)).fetchall()
 await i.response.send_message("🏆 **Cwe Coins leaderboard**\\n"+("\\n".join(f"{n+1}. <@{u}> — {coins}" for n,(u,coins) in enumerate(rows)) or "No balances yet."))


RULES_TEXT = """<:static:1561281643443134564> **CWE SERVER RULES** 💙

**1. 🤝 Respect Everyone** — No bullying, harassment, discrimination or hate speech.
**2. 🚫 No Spamming** — Avoid spam, mass mentions or command flooding.
**3. 🔞 Keep It Family-Friendly** — No NSFW or disturbing content.
**4. 📢 No Advertising** — Get staff permission before advertising.
**5. 🎮 Fair Play** — No cheating, exploits or scams.
**6. 💬 Use Correct Channels** — Keep posts and bot commands in the right places.
**7. 🪙 CWE Coins** — Don't abuse or exploit the coin system.
**8. 🔒 Protect Privacy** — Never share private information, passwords or tokens.
**9. 👑 Respect Staff** — Follow reasonable moderator instructions; open a ticket for help.
**10. 💙 Have Fun!** — Be welcoming and enjoy the community.

⚠️ Rule violations may lead to warnings, timeouts, kicks or bans.
**💙 CWE COMMUNITY | Powered by CWE BOT 🤖**"""

@bot.tree.command(name="rules",description="Post the CWE Community server rules")
@app_commands.checks.has_permissions(manage_guild=True)
async def rules(i:discord.Interaction,channel:discord.TextChannel|None=None):
 ch=channel or i.channel
 embed=discord.Embed(description=RULES_TEXT,color=discord.Color.blurple())
 embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1561281643443134564.webp?size=80")
 await ch.send(embed=embed,allowed_mentions=discord.AllowedMentions.none())
 await i.response.send_message(f"✅ Rules posted in {ch.mention}",ephemeral=True)


class VerifyButton(discord.ui.Button):
 def __init__(self):super().__init__(label="Verify",style=discord.ButtonStyle.success,emoji="✅",custom_id="cwe:verify")
 async def callback(self,i:discord.Interaction):
  row=DB.execute("SELECT role FROM member_roles WHERE guild=?",(i.guild.id,)).fetchone()
  role=i.guild.get_role(row[0]) if row else None
  if not role:return await i.response.send_message("Verification hasn't been configured.",ephemeral=True)
  if role in i.user.roles:return await i.response.send_message("✅ You're already verified.",ephemeral=True)
  try:await i.user.add_roles(role,reason="CWE verification")
  except discord.Forbidden:return await i.response.send_message("❌ Bot needs Manage Roles and its highest role must be above the verified role.",ephemeral=True)
  await i.response.send_message("✅ Verified! Your member channels are now unlocked.",ephemeral=True)

class VerifyView(discord.ui.View):
 def __init__(self):super().__init__(timeout=None);self.add_item(VerifyButton())

@bot.tree.command(name="verifysetup",description="Create a verification panel and lock public channels until verified")
@app_commands.checks.has_permissions(administrator=True)
async def verifysetup(i:discord.Interaction,role:discord.Role,channel:discord.TextChannel):
 await i.response.defer(ephemeral=True)
 if role.is_default() or role.managed or role>=i.guild.me.top_role:
  return await i.followup.send("❌ Choose a normal role below the bot's highest role.",ephemeral=True)
 if not i.guild.me.guild_permissions.manage_channels or not i.guild.me.guild_permissions.manage_roles:
  return await i.followup.send("❌ Bot needs Manage Channels and Manage Roles permissions.",ephemeral=True)
 DB.execute("INSERT OR REPLACE INTO member_roles(guild,role,verify_channel) VALUES (?,?,?)",(i.guild.id,role.id,channel.id));DB.commit()
 # Only hide channels previously public to @everyone; never unlock existing private/staff-only channels.
 changed=0
 for ch in i.guild.channels:
  if ch.id==channel.id or isinstance(ch,discord.CategoryChannel):continue
  everyone=ch.overwrites_for(i.guild.default_role)
  if everyone.view_channel is False:continue
  try:
   await ch.set_permissions(i.guild.default_role,view_channel=False,reason="CWE verification gate")
   await ch.set_permissions(role,view_channel=True,reason="CWE verified role access")
   changed+=1
  except discord.HTTPException as e:print("Verify gate channel failure",ch.id,repr(e),flush=True)
 # Keep verification channel readable by unverified users.
 await channel.set_permissions(i.guild.default_role,view_channel=True,send_messages=False,reason="CWE verification panel")
 embed=discord.Embed(title="CWE VERIFICATION",description="💙 Click **Verify** to unlock the community channels.",color=discord.Color.blurple())
 embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1561281643443134564.webp?size=80")
 await channel.send(embed=embed,view=VerifyView())
 await i.followup.send(f"✅ Verification panel posted in {channel.mention}; gated {changed} previously public channels. Staff-only channels were not changed. Newly created channels need appropriate permissions too.",ephemeral=True)

@bot.tree.command(name="autorole",description="Set the verified member role and post a claim button")
@app_commands.checks.has_permissions(manage_guild=True)
async def autorole(i:discord.Interaction,role:discord.Role,channel:discord.TextChannel):
 if role.is_default() or role.managed or role>=i.guild.me.top_role:
  return await i.response.send_message("❌ Choose a role below the bot's highest role.",ephemeral=True)
 DB.execute("INSERT OR REPLACE INTO member_roles(guild,role,verify_channel) VALUES (?,?,?)",(i.guild.id,role.id,channel.id));DB.commit()
 await channel.send(f"💙 Click below to get {role.mention}.",view=VerifyView())
 await i.response.send_message("✅ Role button set. Automatic assignment at join requires Server Members Intent.",ephemeral=True)


HOOD_CHANNELS = [["📌・INFORMATION",["📜・rules","✅・verify","📢・announcements"],[]],["💬・COMMUNITY",["💬・general","📸・clips","🤖・bot-commands"],[]],["🎮・HOOD GAME",["🎯・hood-chat","🔫・pvp-clips","🆕・game-updates"],["🎮・Hood VC"]],["🎫・SUPPORT",["🎟️・create-ticket"],[]],["👑・STAFF ONLY",["👑・staff-chat"],[]]]

@bot.tree.command(name="setupchannels",description="Create DRILL LIFE Hood Game channel categories")
@app_commands.checks.has_permissions(administrator=True)
async def setupchannels(i:discord.Interaction):
 await i.response.defer(ephemeral=True)
 guild=i.guild
 me=guild.me
 if not me.guild_permissions.manage_channels:
  return await i.followup.send("❌ Give DRILL LIFE BOT Manage Channels permission first.",ephemeral=True)
 made=[]; existing=0; errors=[]
 verified_row=DB.execute("SELECT role,verify_channel FROM member_roles WHERE guild=?",(guild.id,)).fetchone()
 verified=guild.get_role(verified_row[0]) if verified_row else None
 for category_name,text_names,voice_names in HOOD_CHANNELS:
  staff=category_name.startswith("👑")
  cat=discord.utils.get(guild.categories,name=category_name)
  if cat is None:
   overwrites={guild.default_role:discord.PermissionOverwrite(view_channel=False)} if staff else None
   try:
    cat=await guild.create_category(category_name,overwrites=overwrites,reason="DRILL LIFE channel setup")
    made.append(category_name)
   except discord.HTTPException as e:
    errors.append(category_name);print("Category create failed",repr(e),flush=True);continue
  for name,kind in [(n,"text") for n in text_names]+[(n,"voice") for n in voice_names]:
   collection=cat.text_channels if kind=="text" else cat.voice_channels
   if discord.utils.get(collection,name=name):
    existing+=1;continue
   perms=None
   if staff:
    perms={guild.default_role:discord.PermissionOverwrite(view_channel=False)}
   elif verified and category_name not in ("📌・INFORMATION",):
    perms={guild.default_role:discord.PermissionOverwrite(view_channel=False),verified:discord.PermissionOverwrite(view_channel=True)}
   elif name.startswith("✅・verify"):
    perms={guild.default_role:discord.PermissionOverwrite(view_channel=True,send_messages=False)}
   try:
    if kind=="text":await guild.create_text_channel(name,category=cat,overwrites=perms,reason="DRILL LIFE channel setup")
    else:await guild.create_voice_channel(name,category=cat,overwrites=perms,reason="DRILL LIFE channel setup")
    made.append(name)
   except discord.HTTPException as e:
    errors.append(name);print("Channel create failed",repr(e),flush=True)
 await i.followup.send(f"✅ Created **{len(made)}** categories/channels. Already existed: **{existing}**. Errors: **{len(errors)}**. Staff channels are private from @everyone. For verified-only access, run /verifysetup with your Verified role and #verify channel. Newly created channels aren't automatically connected to /welcome or /ticketsetup.",ephemeral=True)


@bot.tree.command(name="previewcleanup",description="Show old channels that are outside the new Hood Game layout")
@app_commands.checks.has_permissions(administrator=True)
async def previewcleanup(i:discord.Interaction):
 expected={name for category,texts,voices in HOOD_CHANNELS for name in [category,*texts,*voices]}
 old=[ch for ch in i.guild.channels if ch.name not in expected]
 summary="\\n".join(f"• {ch.name} ({ch.id})" for ch in old[:30])
 if len(old)>30:summary+=f"\\n...and {len(old)-30} more"
 await i.response.send_message(f"🔎 **Old channels/categories:** {len(old)}\\n{summary or 'None'}\\n\\nNothing was deleted.",ephemeral=True)

@bot.tree.error
async def errors(i:discord.Interaction,error):
 msg="❌ Missing permissions or an error occurred. Check the bot's channel permissions."
 if not i.response.is_done():await i.response.send_message(msg,ephemeral=True)
 print("Command error:",repr(error),flush=True)

@bot.event
async def setup_hook():
 bot.add_view(OpenView());bot.add_view(CloseView());bot.add_view(VerifyView())

bot.run(TOKEN)
