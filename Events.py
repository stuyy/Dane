import discord
from discord.ext import commands
import time
import datetime 
import random
from database.database import load_db
import threading
import asyncio

bucket = commands.CooldownMapping.from_cooldown(3, 5, commands.BucketType.member)

count = 0

class DaneBotEvents(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.database = load_db('./config/config.json')

    @commands.Cog.listener()
    async def on_ready(self):
        print('Logged in as ' + self.client.user.name + '#' + self.client.user.discriminator)
        print(self.database)
        await self.client.change_presence(activity=discord.Game('Coding for ' + str(len(self.client.guilds))  + ' guilds.'))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        embed = discord.Embed()
        embed.title = 'Error'
        embed.description = str(error)
        await ctx.channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message_delete(self, message): # Print out a summary of the message deleted

        if message.author.bot:
            return
        msgString = message.content
        msgAuthor = message.author
        time = utc_to_local(message.created_at)
        id = message.id

        embed = discord.Embed(color=16007746)

        embed.title = "Message Deleted <" + str(id) +">"

        embed.add_field(name="Author", value=msgAuthor, inline=False)
        embed.add_field(name="Time", value=time, inline=False)
        embed.add_field(name="Message ID", value=id, inline=False)
        embed.add_field(name="Message", value=msgString)
        embed.set_author(name=msgAuthor, icon_url=msgAuthor.avatar_url)

        channels = message.guild.channels
        mod_channel = discord.utils.get(channels, name='mod-logs')
        await mod_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        
        # Add user to database
        try:
            cursor = self.database.cursor()
            cursor.execute("INSERT INTO Users VALUES(" + str(member.id) + "," + str(member.guild.id) + ", DEFAULT)")
            self.database.commit()
        except Exception as err:
            print(err)

        try:
            embed = discord.Embed(color=4303348)
            embed.set_author(name=self.client.user.name, icon_url=member.avatar_url)
            embed.set_footer(text="User joined")
            # Add user to Great Dane Role. 
        except Exception as err:
            print(err)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.bot:
            pass
        else:
            member_log_channel = discord.utils.get(member.guild.channels, name='member-log')
            authorName = member.name + "#" + member.discriminator + " <" + str(member.id) + ">"
            embed = discord.Embed(color=16007489)
            embed.set_author(name=authorName, icon_url=member.avatar_url)
            embed.set_footer(text="User left")
            await member_log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        member_log_channel = discord.utils.get(member.guild.channels, name='mod-logs')
        authorName = member.name + "#" + member.discriminator + " <" + str(member.id) + ">"
        embed = discord.Embed(color=16029762)
        embed.set_author(name=authorName, icon_url=member.avatar_url)
        embed.set_footer(text="User Banned")
        await member_log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        member_log_channel = discord.utils.get(guild.channels, name='mod-logs')
        authorName = user.name + "#" + user.discriminator + " <" + str(user.id) + ">"
        embed = discord.Embed(color=8314597)
        embed.set_author(name=authorName, icon_url=user.avatar_url)
        embed.set_footer(text="User Unbanned")
        await member_log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        print(guild.id)
        cursor = self.database.cursor()
        cursor.execute("INSERT INTO Guilds VALUES(" + str(guild.id) + ", DEFAULT, DEFAULT, DEFAULT)")
        self.database.commit()
        print("Done.")
        # Every Guild needs a mod-logs channel, mute role

        dane_logs_channel = discord.utils.get(guild.channels, name='dane-logs')
        if dane_logs_channel is not None:
            embed = discord.Embed()
            embed.title = 'Dane Bot Joined ' + guild.name
            embed.description = 'Dane Bot automatically looks for the channel dane-logs and keeps all mod and error messages in there.'
            await dane_logs_channel.send(embed=embed)
        else:
            # Create Dane Log Channel.
            pass
    @commands.Cog.listener()
    async def on_message(self, message):
        global count
        if message.author.bot:
            return
        '''
        if user is spamming, the bot will mute them.
        The bot queries the database to find the mute_role, which is the role to apply to the user.
        If mute_role is 0, then the bot will create a role called 'Muted by Dane' with permissions preventing the user from sending messages.
        The bot will update the column mute_role with the role id, and then overwrite all channel permissions for the new Muted role, and then adds the user to the role.
        '''
        if bucket.update_rate_limit(message):
            print(message.author.name + ' is sending messages too fast!')
            #cursor = self.database.cursor()
            #cursor.execute("SELECT mute_role FROM Guilds where guild_id = " + str(message.guild.id))

            muted_role = discord.utils.find(lambda role: role.name == 'Muted by Dane', message.guild.roles)
            if muted_role is not None:
                print("Role exists.")
                await message.author.add_roles(muted_role, reason="Spamming")
            else:
                muted_role = await message.guild.create_role(name='Muted by Dane') # Create the role...
                all_channels = message.guild.channels
                overwrite = discord.PermissionOverwrite()
                overwrite.send_messages=False
                overwrite.read_messages=True

                for channel in all_channels:
                    if channel.permissions_for(message.guild.me).manage_roles: # If the bot can manage permissions for channel, then overrwrite.
                        await channel.set_permissions(muted_role, overwrite=overwrite)
                    else:
                        print("No permissions to update roles for channel " + channel.name)

                # Mute the user by giving them the Muted role.
                await message.author.add_roles(muted_role, reason="User was spamming.")
            embed = discord.Embed()
            embed.title='Administrator Message'
            embed.description=message.author.name + ' was muted for 10 seconds.'
            await message.channel.send(embed=embed)
            await asyncio.sleep(10) # Sleep for 60 seconds, and then unmute the user.
            await message.author.remove_roles(muted_role, reason="Unmuting...")
            return
        elif message.content.startswith(self.client.command_prefix):
            return
        else:
            xp = generate_xp()
            # Give User XP
            cursor = self.database.cursor()
            cursor.execute("SELECT client_xp, client_level FROM UserLevelData WHERE client_id=" + str(message.author.id) + " AND guild_id = " + str(message.guild.id))
            results = cursor.fetchall()
            try:
                if len(results) == 0:
                    cursor.execute("INSERT INTO UserLevelData VALUES(" + str(message.author.id) + ", " +  str(message.guild.id) + ",  " + str(xp) + ", 1)")
                    self.database.commit()
                    print("Done.")
                else:
                    currentXP = results[0][0]
                    currentLevel = results[0][1]
                    updatedXP = int(currentXP) + xp
                    flag =  False

                    if updatedXP < 500:
                        currentLevel = 1
                    elif updatedXP > 500 and currentXP < 1200:
                        if currentLevel != 2:
                            currentLevel = 2
                            flag = True
                    elif updatedXP > 1200 and currentXP < 2500:
                        if currentLevel != 3:
                            currentLevel = 3
                            flag = True
                    elif updatedXP > 2500 and currentXP < 3950:
                        if currentLevel != 4:
                            currentLevel = 4
                            flag = True
                    else:
                        pass
                    # Update User XP and Level
                    try:
                        cursor.execute("UPDATE UserLevelData SET client_xp = " + str(updatedXP) + ", client_level = " + str(currentLevel) +" WHERE client_id = " + str(message.author.id) + " AND guild_id=" + str(message.guild.id))
                        self.database.commit()
                        print('updated user xp for ' + message.author.name)
                    except Exception as err:
                        print(err)

                    if flag:
                        # Send embed
                        embed = discord.Embed()
                        embed.title = 'Level Up!'
                        embed.description = '<@'+str(message.author.id)+'> leveled up to level ' + str(currentLevel)
                        await message.channel.send(embed=embed)
                    else:
                        pass

            except Exception as err:
                print(err)
            # give xp

'''
function used to convert utc to local time
'''
def utc_to_local(dt):
    if time.localtime().tm_isdst:
        return dt - datetime.timedelta(seconds = time.altzone)
    else:
        return dt - datetime.timedelta(seconds = time.timezone)

def generate_xp():
    return random.randint(1, 150)

def setup(bot):
    bot.add_cog(DaneBotEvents(bot))