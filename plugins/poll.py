from datetime import datetime

from utils.base import HootPlugin, CommandLevels

from disco.types.message import MessageEmbed
from gevent import sleep
from gevent.timeout import Timeout


class PollPlugin(HootPlugin):

    LETTERS = [chr(127462 + i) for i in range(26)]  # Emoji alphabet

    @HootPlugin.listen("Ready")
    def on_ready(self, _):
        self.poll_channel = self.client.api.channels_get(self.config['poll_channel'])
        for msg in self.poll_channel.get_pins():
            if msg.author.id == self.client.state.me.id:
                self.poll_msg = msg
                break
        else:
            self.poll_msg = None

        self.sub_role = next(r for r in
                             self.client.api.guilds_roles_list(self.config['GUILD_ID']) if
                             r.id == self.config['subscribe_role'])


    def get_msg(self, event):
        masync = self.wait_for_event("MessageCreate", channel_id=event.msg.channel_id, author__id=event.msg.author.id)
        try:
            return masync.get(timeout=self.config['question_timeout'])
        except Timeout:
            event.msg.reply("No answer provided, canceling")
            return None

    @HootPlugin.command("poll", "<question:str...>", level=CommandLevels.MOD)
    def create_poll(self, event, question: str):
        """
        ***The Poll Command***

        This command will create a new poll and post it.

        ***Required Values***
        > __question__ **The poll question**
        """
        responses = {}
        for letter in self.LETTERS:
            event.msg.reply("Response {}: Send 'exit' to post, 'cancel' to cancel the poll".format(letter))
            msg = self.get_msg(event)
            if msg is None:
                return
            if msg.content == 'exit':
                break
            if msg.content == 'cancel':
                return
            responses[letter] = msg.content

        if self.poll_msg:
            self.poll_msg.unpin()

        embed = MessageEmbed()
        embed.title = "New poll question!"
        embed.color = 0x6832E3
        embed.timestamp = datetime.utcnow().isoformat()
        embed.description = "\n".join([question + "\n"] + [l + " **" + q + "**" for l, q in responses.items()])
        self.sub_role.update(mentionable=True)
        sleep(.5)
        poll_msg = self.poll_channel.send_message(self.sub_role.mention, embed=embed)
        self.sub_role.update(mentionable=False)
        self.poll_msg = poll_msg
        self.poll_msg.pin()
        for emoji in responses:
            sleep(.5)
            self.poll_msg.add_reaction(emoji)

    @HootPlugin.command("subscribe")
    def subscribe_member(self, event):
        """
        ***The Subscribe Command***

        This adds the subscriber role, so you can be notified when a new poll is posted.
        """
        if self.sub_role.id not in event.member.roles:
            event.member.add_role(self.sub_role)
        event.msg.add_reaction("👍")

    @HootPlugin.command("unsubscribe")
    def unsubscribe_member(self, event):
        """
        ***The Unsubscribe Command***

        This removes the subscriber role
        """
        if self.sub_role.id in event.member.roles:
            event.member.remove_role(self.sub_role)
        event.msg.add_reaction("👍")
