import re
import configfile
import socket
import time
import errno
import queue
from select import select

__config_inst = configfile.Configuration()
config = __config_inst.config

class Connection:
    socket = None
    parent = None
    connected = False
    sendqueue = queue.Queue()
    recvqueue = queue.Queue()
    buf = ""

    def __init__(self, net):
        self.net = net
        self.ip = config['servers'][net]['ip']
        self.port = config['servers'][net]['port']
        self.serverpass = config['servers'][net]['password']

    def disconnect(self, message=None):
        if self.socket:
            self.connected = False
            try:
                self.socket.sendall(bytes("QUIT :%s" % message, "utf-8"))
                self.socket.close()
            except:
                pass
            self.socket = None

    def connect(self):
        if not self.socket:
            try:
                self.socket = socket.create_connection((self.ip,self.port))
                self.socket.setblocking(0)
                if self.serverpass:
                    self.send("PASS %s" % self.serverpass)
                self.connected = True
            except:
                self.socket = None
        return self.socket != None

    def run(self):
        if self.connected:
            try:
                for s in select ([self.socket], [], [], 0.0):
                    for sock in s:
                        self.buf += str(self.socket.recv(4096), "utf-8")
                        lines = self.buf.split("\r\n")
                        self.buf = lines[-1]
                        for line in lines[:-1]:
                            self.recvqueue.put(line, False)

                if not self.sendqueue.empty():
                    try:
                        data = self.sendqueue.get(False)
                        print(">%s" % data)
                        self.socket.sendall(bytes("%s\r\n" % data, "utf-8"))
                    except queue.Empty:
                        pass
            except socket.error as err:
                print("Error: %s" % err.args[1])
                self.disconnect()
                return False
            return True
        return False

    def send(self, data):
        if self.connected:
            self.sendqueue.put(data, False)

    def get(self):
        if self.recvqueue.empty():
            return None
        try:
            return self.recvqueue.get(False)
        except:
            return None


_rfc_1459_command_regexp = re.compile("^(:(?P<prefix>[^ ]+) +)?(?P<command>[^ ]+)( *(?P<argument>.+))?")

if __name__ == "__main__":
    net = Connection("Rizon")
    net.connect()
    try:
        net.send("NICK %s" % config['user']['nickname'])
        net.send("USER %s 0 * :%s" % (config['user']['username'], config['user']['realname']))
        while net.run():
            line = net.get()
            while line is not None:
                m = _rfc_1459_command_regexp.match(line)
                if m.group('command') == 'PRIVMSG':
                    sender = m.group('prefix').split('!')
                    parts = m.group('argument').split(' :')
                    print("< <%s:%s> %s" % (sender[0], parts[0], ' :'.join(parts[1:])))
                else:
                    print("<%s -- %s -- %s" % (m.group('prefix'), m.group('command'), m.group('argument')))

                if m.group('command') == 'PING':
                    net.send("PONG %s" % m.group('argument'))
                elif m.group('command') == '376':
                    net.send("JOIN #shameimaru")
                elif m.group('command') == 'ERROR':
                    net.disconnect()
                line = net.get()
            time.sleep(0.5)
        net.disconnect()
    except KeyboardInterrupt:
        net.disconnect("Ctrl+C")
    except:
        net.disconnect("Error")

_linesep_regexp = re.compile("\r?\n")

_LOW_LEVEL_QUOTE = "\x0F"
_CTCP_LEVEL_QUOTE = "\x5C"
_CTCP_DELIMITER = "\x01"

_low_level_mapping = {
    "0": "\x00",
    "n": "\n",
    "r": "\r",
    _LOW_LEVEL_QUOTE: _LOW_LEVEL_QUOTE
}

_low_level_regexp = re.compile(_LOW_LEVEL_QUOTE + "(.)")

# Numeric table mostly stolen from the Perl IRC module (Net::IRC).
numeric_events = {
    "001": "welcome",
    "002": "yourhost",
    "003": "created",
    "004": "myinfo",
    "005": "featurelist",    # XXX
    "200": "tracelink",
    "201": "traceconnecting",
    "202": "tracehandshake",
    "203": "traceunknown",
    "204": "traceoperator",
    "205": "traceuser",
    "206": "traceserver",
    "207": "traceservice",
    "208": "tracenewtype",
    "209": "traceclass",
    "210": "tracereconnect",
    "211": "statslinkinfo",
    "212": "statscommands",
    "213": "statscline",
    "214": "statsnline",
    "215": "statsiline",
    "216": "statskline",
    "217": "statsqline",
    "218": "statsyline",
    "219": "endofstats",
    "221": "umodeis",
    "231": "serviceinfo",
    "232": "endofservices",
    "233": "service",
    "234": "servlist",
    "235": "servlistend",
    "241": "statslline",
    "242": "statsuptime",
    "243": "statsoline",
    "244": "statshline",
    "250": "luserconns",
    "251": "luserclient",
    "252": "luserop",
    "253": "luserunknown",
    "254": "luserchannels",
    "255": "luserme",
    "256": "adminme",
    "257": "adminloc1",
    "258": "adminloc2",
    "259": "adminemail",
    "261": "tracelog",
    "262": "endoftrace",
    "263": "tryagain",
    "265": "n_local",
    "266": "n_global",
    "300": "none",
    "301": "away",
    "302": "userhost",
    "303": "ison",
    "305": "unaway",
    "306": "nowaway",
    "311": "whoisuser",
    "312": "whoisserver",
    "313": "whoisoperator",
    "314": "whowasuser",
    "315": "endofwho",
    "316": "whoischanop",
    "317": "whoisidle",
    "318": "endofwhois",
    "319": "whoischannels",
    "321": "liststart",
    "322": "list",
    "323": "listend",
    "324": "channelmodeis",
    "329": "channelcreate",
    "331": "notopic",
    "332": "currenttopic",
    "333": "topicinfo",
    "341": "inviting",
    "342": "summoning",
    "346": "invitelist",
    "347": "endofinvitelist",
    "348": "exceptlist",
    "349": "endofexceptlist",
    "351": "version",
    "352": "whoreply",
    "353": "namreply",
    "361": "killdone",
    "362": "closing",
    "363": "closeend",
    "364": "links",
    "365": "endoflinks",
    "366": "endofnames",
    "367": "banlist",
    "368": "endofbanlist",
    "369": "endofwhowas",
    "371": "info",
    "372": "motd",
    "373": "infostart",
    "374": "endofinfo",
    "375": "motdstart",
    "376": "endofmotd",
    "377": "motd2",                # 1997-10-16 -- tkil
    "381": "youreoper",
    "382": "rehashing",
    "384": "myportis",
    "391": "time",
    "392": "usersstart",
    "393": "users",
    "394": "endofusers",
    "395": "nousers",
    "401": "nosuchnick",
    "402": "nosuchserver",
    "403": "nosuchchannel",
    "404": "cannotsendtochan",
    "405": "toomanychannels",
    "406": "wasnosuchnick",
    "407": "toomanytargets",
    "409": "noorigin",
    "411": "norecipient",
    "412": "notexttosend",
    "413": "notoplevel",
    "414": "wildtoplevel",
    "421": "unknowncommand",
    "422": "nomotd",
    "423": "noadmininfo",
    "424": "fileerror",
    "431": "nonicknamegiven",
    "432": "erroneusnickname",
    "433": "nicknameinuse",
    "436": "nickcollision",
    "437": "unavailresource",    # "Nick temporally unavailable"
    "441": "usernotinchannel",
    "442": "notonchannel",
    "443": "useronchannel",
    "444": "nologin",
    "445": "summondisabled",
    "446": "usersdisabled",
    "451": "notregistered",
    "461": "needmoreparams",
    "462": "alreadyregistered",
    "463": "nopermforhost",
    "464": "passwdmismatch",
    "465": "yourebannedcreep", # I love this one...
    "466": "youwillbebanned",
    "467": "keyset",
    "471": "channelisfull",
    "472": "unknownmode",
    "473": "inviteonlychan",
    "474": "bannedfromchan",
    "475": "badchannelkey",
    "476": "badchanmask",
    "477": "nochanmodes",    # "Channel doesn't support modes"
    "478": "banlistfull",
    "481": "noprivileges",
    "482": "chanoprivsneeded",
    "483": "cantkillserver",
    "484": "restricted",     # Connection is restricted
    "485": "uniqopprivsneeded",
    "491": "nooperhost",
    "492": "noservicehost",
    "501": "umodeunknownflag",
    "502": "usersdontmatch",
}

generated_events = [
    # Generated events
    "dcc_connect",
    "dcc_disconnect",
    "dccmsg",
    "disconnect",
    "ctcp",
    "ctcp_reply",
]

protocol_events = [
    # IRC protocol events
    "error",
    "join",
    "kick",
    "mode",
    "part",
    "ping",
    "privmsg",
    "notice",
    "quit",
    "invite",
    "pong",
]

_all_irc_events = generated_events + protocol_events + [numeric_events.values()]
