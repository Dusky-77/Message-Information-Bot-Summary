from __future__ import annotations

import os
from dotenv import load_dotenv
import discord
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# bot setup

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="=", intents=intents, help_command=None)

ACCENT = discord.Colour(0x51AFFF)  # blue accent bar on containers


# helpers

async def find_message(guild: discord.Guild, message_id: int) -> discord.Message | None:
    """
    Search every readable text channel + thread (including active threads)
    across the entire guild for message_id.
    """
    seen: set[int] = set()
    channels: list[discord.abc.Messageable] = []

    for ch in guild.channels:
        if isinstance(ch, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
            channels.append(ch)
        if isinstance(ch, discord.TextChannel):
            # cached threads in that channel
            channels.extend(ch.threads)

    # also pull active threads that may not be in channel.threads yet
    try:
        active = await guild.active_threads()
        channels.extend(active)
    except Exception:
        pass

    for ch in channels:
        if ch.id in seen:
            continue
        seen.add(ch.id)
        try:
            return await ch.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            continue

    return None


def unix(dt) -> int | None:
    return int(dt.timestamp()) if dt else None


def b(val) -> str:
    """Boolean to backtick-formatted TRUE/FALSE."""
    return "`TRUE`" if val else "`FALSE`"


def nn(val) -> str:
    """Value or NULL."""
    return f"`{val}`" if val is not None else "`NULL`"


def sep() -> discord.ui.Separator:
    return discord.ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small)


def chunk_text(text: str, limit: int = 3900) -> list[str]:
    """Split long text into chunks, each under `limit` chars."""
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            parts.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        parts.append(current)
    return parts


# views

class MessageDetailsView(discord.ui.LayoutView):
    """
    Full Components V2 layout for =message.
    All sections are built dynamically in __init__ and added via add_item.
    """

    def __init__(
        self,
        *,
        jump_url: str,
        activity_text: str,
        app_text: str,
        author_text: str,
        avatar_url: str,
        other_text: str,
        att_text: str,
        content_preview: str,
    ):
        super().__init__()

        # outer top separator
        self.add_item(sep())

        # build container children
        children: list = [
            # header row: title + jump button
            discord.ui.Section(
                discord.ui.TextDisplay(content="## Message Data"),
                accessory=discord.ui.Button(
                    url=jump_url,
                    style=discord.ButtonStyle.link,
                    label="Jump To Message",
                    emoji="🔗",
                ),
            ),
            sep(),
            discord.ui.TextDisplay(content=content_preview),
            sep(),
            discord.ui.TextDisplay(content=activity_text),
            sep(),
            discord.ui.TextDisplay(content=app_text),
            sep(),
            # author row: text + avatar thumbnail
            discord.ui.Section(
                discord.ui.TextDisplay(content=author_text),
                accessory=discord.ui.Thumbnail(media=avatar_url),
            ),
            sep(),
            discord.ui.TextDisplay(content=other_text),
            sep(),
            discord.ui.TextDisplay(content=att_text),
            sep(),
        ]

        self.add_item(discord.ui.Container(*children, accent_colour=ACCENT))

        # outer bottom separator
        self.add_item(sep())


class CheckReactionsView(discord.ui.LayoutView):
    """
    Components V2 layout for =checkreactions.
    reaction_blocks = list of (header_text, [chunk_str, ...]) — one entry per emoji.
    """

    def __init__(self, *, header: str, reaction_blocks: list[tuple[str, list[str]]]):
        super().__init__()

        self.add_item(sep())

        container_children: list = [
            sep(),
            discord.ui.TextDisplay(content=header),
            sep(),
        ]

        for i, (block_header, chunks) in enumerate(reaction_blocks):
            container_children.append(discord.ui.TextDisplay(content=block_header))
            for chunk in chunks:
                container_children.append(discord.ui.TextDisplay(content=chunk))
            # separator between reactions, but not after the last one
            if i < len(reaction_blocks) - 1:
                container_children.append(sep())

        container_children.append(sep())

        self.add_item(discord.ui.Container(*container_children, accent_colour=ACCENT))
        self.add_item(sep())


# commands

@bot.hybrid_command(name="message", description="Get full statistics for any message by ID — searches every channel in the server")
@commands.guild_only()
async def message_cmd(ctx: commands.Context, message_id: str):
    """=message <message_id>"""
    await ctx.defer()

    try:
        mid = int(message_id)
    except ValueError:
        await ctx.send("❌ That doesn't look like a valid message ID.", ephemeral=True)
        return

    msg = await find_message(ctx.guild, mid)
    if msg is None:
        await ctx.send(
            "❌ Message not found in any channel/thread in this server. "
            "Make sure the bot has Read Message History permission.",
            ephemeral=True,
        )
        return

    author = msg.author

    # content preview
    preview = msg.content[:300] + ("…" if len(msg.content) > 300 else "") if msg.content else "*[no text content]*"
    content_preview = (
        f"### Content Preview:\n"
        f"```\n{preview}\n```\n"
        f"- Character count: `{len(msg.content)}`\n"
        f"- Word count: `{len(msg.content.split())}`"
    )

    # activity 
    act = getattr(msg, "activity", None)
    ai  = getattr(msg, "activity_instance", None)
    activity_text = (
        f"### Activity Details:\n"
        f"1. Is an activity? {b(act)}"
        + (f"\n      - Type: `{act.get('type', 'N/A')}`\n      - Party ID: `{act.get('party_id', 'N/A')}`" if act else "")
        + f"\n2. Is an activity instance? {b(ai)}"
        + (f"\n      - Instance ID: `{ai}`" if ai else "")
    )

    # application
    app = getattr(msg, "application", None)
    app_text = (
        f"### Application Details:\n"
        f"1. Is an application? {b(app)}"
        + (f"\n      - Name: `{getattr(app, 'name', app)}`" if app else "")
        + f"\n2. Application ID: {nn(msg.application_id)}\n"
        f"3. Interaction? {b(msg.interaction_metadata)}"
        + (f"\n      - Type: `{msg.interaction_metadata.type.name}`\n      - Name: `{msg.interaction_metadata.name}`" if msg.interaction_metadata else "")
    )

    # author — fetch banner via REST
    avatar_url = str(author.display_avatar.url)
    banner_url: str | None = None
    try:
        full_user = await bot.fetch_user(author.id)
        banner_url = str(full_user.banner.url) if full_user.banner else None
    except Exception:
        pass

    member: discord.Member | None = ctx.guild.get_member(author.id)
    global_name = getattr(author, "global_name", None)

    author_text = (
        f"### Author Details:\n"
        f"1. Author ID: `{author.id}`\n"
        f"2. Username: `{author.name}`\n"
        f"3. Global Name: `{global_name or 'N/A'}`\n"
        f"4. Avatar: `{'SET' if author.avatar else 'NOT SET'}`\n"
        f"5. Banner: `{'SET' if banner_url else 'NOT SET'}`"
        + (f"\n      - {banner_url}" if banner_url else "")
        + f"\n6. Bot? {b(author.bot)}\n"
        f"7. System? {b(author.system)}\n"
        f"8. Account Created: <t:{unix(author.created_at)}:d> | <t:{unix(author.created_at)}:T>\n"
        f"9. NSFW Allowed: `N/A`\n"
        f"10. Blocked? `N/A`"
    )
    if member:
        roles_list = [r.mention for r in reversed(member.roles[1:])]
        roles_str  = " ".join(roles_list) if roles_list else "`None`"
        author_text += (
            f"\n11. Server Nickname: `{member.nick or 'NOT SET'}`\n"
            f"12. Joined Server: <t:{unix(member.joined_at)}:d> | <t:{unix(member.joined_at)}:T>\n"
            f"13. Top Role: {member.top_role.mention}\n"
            f"14. All Roles ({len(roles_list)}): {roles_str[:600]}"
            + ("…" if len(roles_str) > 600 else "")
        )

    # reactions 
    if msg.reactions:
        reactions_part = "`TRUE`\n"
        for r in msg.reactions:
            burst_tag = f" (+{r.burst_count} burst)" if r.burst_count else ""
            reactions_part += f"      - `{str(r.emoji)}` × **{r.count}**{burst_tag}\n"
    else:
        reactions_part = "`FALSE`\n"

    # mentions 
    mc = ", ".join(f"`{c.id}`" for c in msg.channel_mentions) if msg.channel_mentions else "`None`"
    mr = ", ".join(r.mention for r in msg.role_mentions)       if msg.role_mentions    else "`None`"
    um = ", ".join(u.mention for u in msg.mentions)            if msg.mentions         else "`None`"

    # edited 
    edited_part = f"4. Edited? {b(msg.edited_at)}"
    if msg.edited_at:
        edited_part += f"\n      - Timestamp: <t:{unix(msg.edited_at)}:d> | <t:{unix(msg.edited_at)}:T>"

    # other
    other_text = (
        f"### Other Details:\n"
        f"1. Channel: {msg.channel.mention} (`{msg.channel.id}`)\n"
        f"2. Channel Type: `{msg.channel.type.name}`\n"
        f"3. Components (legacy V1): {b(msg.components)} (`{len(msg.components)}`)\n"
        + edited_part + "\n"
        f"5. Embeds: {b(msg.embeds)} (`{len(msg.embeds)}`)\n"
        f"6. Message ID: `{msg.id}`\n"
        f"7. Message Type: `{msg.type.name}`\n"
        f"8. Flags Raw: `{msg.flags.value}`\n"
        f"9. Mention Channels: {mc}\n"
        f"10. Mentioned (bot in message): {b(msg.mentions)}\n"
        f"11. Mention @everyone: {b(msg.mention_everyone)}\n"
        f"12. Mention Roles: {mr}\n"
        f"13. User Mentions: {um}\n"
        f"14. Pinned: {b(msg.pinned)}\n"
        f"15. Reactions: {reactions_part}"
        f"16. Reference (reply to): {b(msg.reference)}"
        + (f"\n      - Message ID: `{msg.reference.message_id}`" if msg.reference else "")
        + f"\n17. State: `SENT`\n"
        f"18. Stickers: {b(msg.stickers)} (`{len(msg.stickers)}`)\n"
        f"19. Timestamp: <t:{unix(msg.created_at)}:d> | <t:{unix(msg.created_at)}:T>\n"
        f"20. TTS: {b(msg.tts)}\n"
        f"21. Webhook? {b(msg.webhook_id)}"
        + (f"\n      - Webhook ID: `{msg.webhook_id}`" if msg.webhook_id else "")
    )

    # attachments
    att_text = f"### Attachment Details:\n1. Attachments: {b(msg.attachments)} (`{len(msg.attachments)}`)"
    for att in msg.attachments:
        att_text += f"\n\n**{att.filename}**\n"
        att_text += f"- Content Type: `{att.content_type or 'N/A'}`\n"
        if att.height:
            att_text += f"- Dimensions: `{att.width} × {att.height} px`\n"
        att_text += (
            f"- Size: `{att.size:,} bytes`\n"
            f"- ID: `{att.id}`\n"
            f"- Spoiler: {b(att.is_spoiler())}\n"
            f"- Ephemeral: {b(att.ephemeral)}\n"
            f"- URL: {att.url}"
        )

    view = MessageDetailsView(
        jump_url=msg.jump_url,
        activity_text=activity_text,
        app_text=app_text,
        author_text=author_text,
        avatar_url=avatar_url,
        other_text=other_text,
        att_text=att_text,
        content_preview=content_preview,
    )
    await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())


@bot.hybrid_command(name="checkreactions", description="For every reaction on a message, show who in the guild has NOT reacted — searches all channels")
@commands.guild_only()
async def checkreactions_cmd(ctx: commands.Context, message_id: str):
    """=checkreactions <message_id>"""
    await ctx.defer()

    try:
        mid = int(message_id)
    except ValueError:
        await ctx.send("Invalid message ID.", ephemeral=True)
        return

    msg = await find_message(ctx.guild, mid)
    if msg is None:
        await ctx.send(
            "Message not found in any channel/thread in this server.",
            ephemeral=True,
        )
        return

    if not msg.reactions:
        await ctx.send("ℹThis message has no reactions.", ephemeral=True)
        return

    # fetch ALL human guild members once
    all_human: list[discord.Member] = []
    async for member in ctx.guild.fetch_members(limit=None):
        if not member.bot:
            all_human.append(member)
    total = len(all_human)

    # ── build one block per reaction emoji ───────────────────────────────
    # reaction_blocks: list of (stats_text, [member_chunk, ...])
    reaction_blocks: list[tuple[str, list[str]]] = []

    for reaction in msg.reactions:
        emoji_str = str(reaction.emoji)

        # fetch every user who used this reaction
        reacted_ids: set[int] = set()
        async for user in reaction.users(limit=None):
            reacted_ids.add(user.id)

        reacted_count  = sum(1 for m in all_human if m.id in reacted_ids)
        not_reacted    = sorted(
            (m for m in all_human if m.id not in reacted_ids),
            key=lambda m: m.display_name.lower(),
        )

        stats = (
            f"## {emoji_str}  Reaction\n"
            f"- Count: `{reaction.count}`"
            + (f"  (+`{reaction.burst_count}` burst)" if reaction.burst_count else "")
            + f"\n- Reacted: `{reacted_count}` / `{total}`\n"
            f"- Not Reacted: `{len(not_reacted)}` / `{total}`"
        )

        if not_reacted:
            mentions  = " ".join(m.mention for m in not_reacted)
            full_list = f"**Haven't reacted ({len(not_reacted)}):**\n{mentions}"
            member_chunks = chunk_text(full_list)
        else:
            member_chunks = ["**Everyone has reacted!**"]

        reaction_blocks.append((stats, member_chunks))

    # ── header summary ────────────────────────────────────────────────────
    emoji_list = " ".join(str(r.emoji) for r in msg.reactions)
    header = (
        f"## Reaction Check\n"
        f"- Message: {msg.jump_url}\n"
        f"- Total human members: `{total}`\n"
        f"- Reactions on message ({len(msg.reactions)}): {emoji_list}"
    )

    # Discord caps a LayoutView at 40 total components
    # If there are so many reactions+chunks that we'd exceed 40, send
    # multiple follow-up messages (one Container per reaction).
    # Each block costs roughly: 1 stats TextDisplay + N chunk TextDisplays + 1 sep = N+2
    # Container overhead: 2 seps inside + 1 header TD + 1 sep = 4 fixed
    # Outer items: sep + Container + sep = 3
    # Conservative threshold: send as one view if ≤ 6 total TextDisplays across all blocks.
    total_tds = sum(1 + len(chunks) for _, chunks in reaction_blocks)  # stats TD + chunk TDs

    if total_tds + 4 + 3 <= 38:  # fits comfortably in one view
        view = CheckReactionsView(header=header, reaction_blocks=reaction_blocks)
        await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())
    else:
        # send header message first, then one message per reaction
        header_view = CheckReactionsView(header=header, reaction_blocks=[])
        await ctx.send(view=header_view)
        for stats, chunks in reaction_blocks:
            view = CheckReactionsView(header=stats, reaction_blocks=[("", chunks)])
            await ctx.send(view=view, allowed_mentions=discord.AllowedMentions.none())


# events

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"   Logged in as {bot.user} (ID: {bot.user.id})")
    print(f"   Serving {len(bot.guilds)} guild(s)")
    print(f"   Prefix: =   |   Slash commands synced")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`", ephemeral=True)
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command can only be used in a server.", ephemeral=True)
    else:
        raise error


# run 

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN not set in .env")
    bot.run(TOKEN)
