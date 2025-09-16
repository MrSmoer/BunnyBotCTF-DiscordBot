import discord
import datetime
from discord.ext import commands

class RegisterAttendance(discord.ui.View):
    def __init__(self, role: discord.Role, log_channel: discord.TextChannel, category: discord.CategoryChannel):
        discord.ui.View.__init__(self)
        self.role = role
        self.log_channel = log_channel
        self.category = category

    @discord.ui.button(label="Click me to Join the CTF!", style=discord.ButtonStyle.success)
    async def button_callback(self, button, interaction):
        await self.log_channel.send(f"User: {interaction.user.name} is now a {self.role.name} and can see the {self.category.jump_url}")
        await interaction.user.add_roles(self.role)
        # await interaction.response.send_modal(MyModal(title="Banana"))
        await interaction.response.defer()


# This allows to protect against server hijacking, it is unlikely there is already a role called
def rolename_from_ctf(name:str):
    return f"{name}-Attendee"

def list_of_attending_members(category: discord.CategoryChannel):
    allowed_members = set()
    # Do i have to iterate through those channels? > Yes, because people could have been added to
    # a Channel manually
    for channel in category.channels:
        for member in category.guild.members:
            perms = channel.permissions_for(member)
            if perms.read_messages:
                allowed_members.add(member)
    return allowed_members

def generate_active_members_listing(category: discord.CategoryChannel):
    allowed_members = list_of_attending_members(category)
    return "\n".join([member.name for member in allowed_members])

class Attendance(commands.Cog):
    def __init__(self, client):
        self.client = client

    perms = discord.Permissions(manage_roles=True, manage_messages=True, manage_channels=True)
    attendance = discord.SlashCommandGroup("attendance", "ctf attendance management",
                                           default_member_permissions=perms)

    # TODO: double check that all the permissions are typed correctly, could fail silently?
    @attendance.command(description="Create a ctf")
    @commands.has_guild_permissions(manage_messages=True,manage_channels=True, manage_roles=True)
    # TODO: check if bot has required permissions
    # TODO: followup if everything succeeded->tell if smth. went wrong (Try-catch)
    # TODO: gen-invite command, that reattaches a bot generated invite to a category and log-channel
    # TODO: log attendances if other role-changes happen
    #       or someone gets the role assigned manually -> keep list of users/scrape together list of users at start
    #       recipients
    # TODO: log with #channel and user-links
    async def create(self, ctx: discord.ApplicationContext, name: str,
                     channel: discord.Option(discord.TextChannel, name="channel", description="Channel to post the invitation in", required=True),
                     log_channel: discord.Option(discord.TextChannel, name="log-channel", description="Channel the log-messages are sent to", required=False),
                     create_default_channels: bool=False,
                     forced: bool=False):

        for cat in ctx.guild.categories:
            if cat.name == name and not forced:
                print("Category already exists")
                await ctx.respond("already exists")
                return

        for ro in ctx.guild.roles:
            if ro == rolename_from_ctf(name) and not forced:
                print("Role with name already exists")
                await ctx.respond("already exists")
                return

        if channel:
            if not channel.can_send():
                await ctx.respond("Can not send in requested channel")
                return

        if not log_channel:
            log_channel = ctx.channel

        await ctx.respond(f"Creating category {name}")

        newrole = await ctx.guild.create_role(name=rolename_from_ctf(name))

        category = await ctx.guild.create_category(name, overwrites= {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            newrole: discord.PermissionOverwrite(view_channel=True)}
        )

        # set topic to index channel in channel overview with the name
        new_channel = await category.create_text_channel(f"{name}-general", topic=name)

        await log_channel.send(f"These people already have access to {category.jump_url}\n{generate_active_members_listing(category)}")

        if create_default_channels:
            for c in ["web", "pwn", "rev", "misc", "crypto", "osint"]:
                await category.create_text_channel(c)
            await category.create_voice_channel("Voice")

        await channel.send(f"Click below to join CTF {name}!",view=RegisterAttendance(newrole, log_channel, category))

    #TODO: add autocompletion
    #TODO: edit response stratus msg after cleanup
    @attendance.command()
    async def cleaunp(self, ctx,category: discord.Option(discord.CategoryChannel, name="category", description="The category associated with the ctf", required=True)):
        await ctx.respond(f"Deleting {category.name}")
        for channel in category.channels:
            await channel.delete()

        for role in category.guild.roles:
            if role.name == rolename_from_ctf(category.name):
                await role.delete()

        await category.delete()

    @attendance.command()
    #TODO: autocompletion
    #TODO: scrape together everybody who attended and was in the log-channel
    #TODO: log with proper links to profile and category
    async def list(self, ctx,
                   category: discord.Option(discord.CategoryChannel, name="category", description="The category associated with the ctf", required=True)):
        await ctx.respond(f"These people attended:\n {generate_active_members_listing(category)}")


def setup(client):
    client.add_cog(Attendance(client))
