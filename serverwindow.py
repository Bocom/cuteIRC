#! /usr/bin/env python3.1

import sys
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt, QTimer
from connection import *
import threading

class ServerWindow(QtGui.QWidget):
    """A debug layout for cuteIRC"""
    connection = None
    connthread = None
    chans = {}
    ready = False
    def __init__(self, net, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.net = net
        self.setWindowTitle("Server: %s" % net)
    
        self.inputField = CustomInput(self)
        self.inputField.command.connect(self.cmd_handle)
    
        self.chatArea = QtGui.QTextBrowser()
        self.chatArea.setOpenLinks(False)
        self.chatArea.setTextInteractionFlags(Qt.TextInteractionFlag(5))
    
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.chatArea)
        vbox.addWidget(self.inputField)
    
        self.setLayout(vbox)
    
        self.resize(800, 600)

    def closeEvent(self, evt):
        self.connection.disconnect()
        for chan in chans:
            chan.close()
        evt.accept()
        #evt.ignore()
    
    def start(self):
        self.chatArea.append("Connecting to %s:%s..." % (config['servers'][self.net]['ip'], config['servers'][self.net]['port']))
        self.ready = False
        self.connection = Connection(self.net)
        self.connection.connect()
        self.connection.send("NICK %s" % config['user']['nickname'])
        self.connection.send("USER %s 0 * :%s" % (config['user']['username'], config['user']['realname']))
        self.conntimer = QTimer(self)
        self.conntimer.timeout.connect(self.run, 200)
        self.conntimer.start(200)

    def run(self):
        if self.connection.run():
            line = self.connection.get()
            while line is not None:
                # TODO: check if the line is targeted at a child window,
                # create one if appropriate, if not paste here.
                m = _rfc_1459_command_regexp.match(line)
                self.srv_handle(m.group('prefix'), m.group('command'), m.group('argument'))
                line = self.connection.get()
        else:
            self.conntimer.stop()
            self.conntimer = None
            self.connection.disconnect()

    def srv_handle(self, source, command, argument):
        if source:
            sender = source.split('!')
        else:
            sender = ("","")
        parts = argument.split(' :')
        destination = parts[0]
        message = ' :'.join(parts[1:])
        
        if command == '439' or command == '001' or command == '002' or command == '003':
            self.chatArea.append("-%s- * %s" % (source, message))
        elif command == 'NOTICE':
            if self.ready:
                # TODO: check to which window this belongs
                self.chatArea.append("-%s- %s" % (sender[0], message))
            else:
                self.chatArea.append("-%s- %s" % (destination, message))
        elif command == '004':
            self.chatArea.append("-%s- * %s" % (source, argument))
        elif command == '005':
            self.chatArea.append("-%s- * %s %s" % (source, destination, message))
        elif command == '042':
            # TODO: figure out what to do with this "unique id"
            self.chatArea.append("-%s- * %s %s" % (source, destination, message))
        elif command == '251' or command == '255':
            self.chatArea.append("-%s- * %s" % (source, message))
        elif command == '252' or command == '253' or command == '254':
            self.chatArea.append("-%s- * %s %s" % (source, destination, message))
        elif command == '265' or command == '266':
            self.chatArea.append("-%s- * %s" % (source, message))
        elif command == '375' or command == '372': # MOTD
            # TODO: have option to hide MOTD
            self.chatArea.append("-%s- * %s" % (source, message))
        elif command == '376':
            # End of MOTD
            self.ready = True
            self.chatArea.append("-%s- * %s" % (source, message))
        elif command == 'MODE':
            self.chatArea.append("* %s sets modes %s on %s" % (sender[0], message, destination))
        elif command == 'PING':
            self.connection.send("PONG %s" % m.group('argument'))
        elif command == 'ERROR':
            self.connection.disconnect()
        elif command == 'JOIN':
            chan = argument[1:]
            if chan in self.chans:
                self.chans[chan].srv_handle(source, command, argument)
            else:
                # The last parameter will change when this becomes a MDI child
                self.chans[chan] = ChannelWindow(self.connection, argument[1:], self, None)
                self.chans[chan].show()
                self.chans[chan].srv_handle(source, command, argument)
        elif command == '332':
            chan = destination.split(' ')[1]
            if chan in self.chans:
                self.chans[chan].srv_handle(source, command, argument)
        elif command == '333':
            info = destination.split(' ')
            chan = info[1]
            if chan in self.chans:
                self.chans[chan].srv_handle(source, command, argument)
        elif command == '353':
            chan = destination.split(' = ')[1]
            if chan in self.chans:
                self.chans[chan].srv_handle(source, command, argument)
        elif command == '366':
            chan = destination.split(' ')[1]
            if chan in self.chans:
                self.chans[chan].srv_handle(source, command, argument)
        elif command == 'KICK':
            chan = destination.split(' ')[0]
            if chan in self.chans:
                self.chans[chan].srv_handle(source, command, argument)
        elif command == '442':
            chan = destination.split(' ')[1]
            if chan in self.chans:
                self.chans[chan].srv_handle(source, command, argument)
        elif command == 'PRIVMSG':
            if message[0] == '\x01':
                # CTCP
                if message[1:7] != 'ACTION':
                    # TODO: check for non-window-specific CTCPs
                    if destination in self.chans:
                        self.chans[destination].srv_handle(source, command, argument)
            if destination in self.chans:
                self.chans[destination].srv_handle(source, command, argument)
            else:
                # The last parameter will change when this becomes a MDI child
                # We open in here as well as on joins because this may be a private message
                self.chans[destination] = ChannelWindow(self.connection, sender[0], self, None)
                self.chans[destination].show()
                self.chans[destination].srv_handle(source, command, argument)
        else:
            print("%s -- %s -- %s" % (source, command, argument))

    def cmd_handle(self, command, args):
        if command == 'join':
            self.connection.send("JOIN %s" % args)
        elif command == 'quit':
            self.connection.disconnect(args)
            self.dispose()

class ChannelWindow(QtGui.QWidget):
    """A debug layout for cuteIRC"""
    connection = None
    chan = None
    def __init__(self, connection, chan, serverwin, parent):
        QtGui.QWidget.__init__(self, parent)

        self.connection = connection
        self.chan = chan
        self.ischan = chan[0] == '#'
        self.serverwin = serverwin
        self.setWindowTitle("%s" % chan)

        self.inputField = CustomInput(self)
        self.inputField.command.connect(self.cmd_handle)

        self.chatArea = QtGui.QTextBrowser()
        self.chatArea.setOpenLinks(False)
        self.chatArea.setTextInteractionFlags(Qt.TextInteractionFlag(5))

        vbox = QtGui.QVBoxLayout()
        
        if self.ischan:
            self.nickList = QtGui.QListWidget()
            self.nickList.setSortingEnabled(True)

            splitter = QtGui.QSplitter()
            splitter.addWidget(self.chatArea)
            splitter.addWidget(self.nickList)
            splitter.setStretchFactor(0, 4)
        
            vbox.addWidget(splitter)
        else:
            vbox.addWidget(self.chatArea)
        
        vbox.addWidget(self.inputField)

        self.setLayout(vbox)

        self.resize(800, 600)

    def closeEvent(self, evt):
        if (self.ischan):
            self.connection.send("PART %s" % self.chan)
        if self.chan in self.serverwin.chans:
            del(self.serverwin.chans[self.chan])

    def run(self):
        if self.connection.run():
            line = self.connection.get()
            while line is not None:
                # TODO: check if the line is targeted at a child window,
                # create one if appropriate, if not paste here.
                m = _rfc_1459_command_regexp.match(line)
                self.srv_handle(m.group('prefix'), m.group('command'), m.group('argument'))
                line = self.connection.get()
        else:
            self.conntimer.stop()
            self.conntimer = None
            self.connection.disconnect()

    def srv_handle(self, source, command, argument):
        sender = source.split('!')
        parts = argument.split(' :')
        destination = parts[0]
        message = ' :'.join(parts[1:])

        if command == 'PRIVMSG':
            if message[0:7] == '\x01ACTION':
                self.chatArea.append("* %s %s" % (sender[0], message[8:-1]))
            else:
                self.chatArea.append("<%s> %s" % (sender[0], message))
        elif command == 'JOIN':
            self.chatArea.append("%s has joined %s" % (sender[0], message))
        elif command == 'MODE':
            self.chatArea.append("* %s sets modes %s on %s" % (sender[0], message, destination))
        elif command == 'NOTICE':
            self.chatArea.append("-%s- %s" % (sender[0], message))
        elif command == '332':
            self.chatArea.append("Topic for %s is: %s" % (self.chan, message))
            self.setWindowTitle("%s: %s" % (self.chan, message))
        elif command == '333':
            info = argument.split(' ')
            sender = info[2].split('!')
            time = info[3]
            self.chatArea.append("Topic for %s set by %s on %s" % (self.chan, sender[0], time))
        elif command == '353':
            names = message.split(' ')
            for n in names:
                self.nickList.addItem(n)
        elif command == '366':
            pass
        elif command == 'KICK':
            # TODO: remove nick from nicklist
            info = destination.split(' ')
            self.chatArea.append("%s was kicked from %s by %s: %s" % (info[1], self.chan, sender[0], message))
        elif command == '442':
            self.chatArea.append("You're not on %s." % (self.chan))
        else:
            print("%s -- %s -- %s" % (source, command, argument))

    def cmd_handle(self, command, args):
        if command == 'say':
            self.chatArea.append("<%s> %s" % (config['user']['nickname'], args))
            self.connection.send("PRIVMSG %s :%s" % (self.chan, args))
        elif command == 'me':
            self.chatArea.append("* %s %s" % (config['user']['nickname'], args))
            self.connection.send("PRIVMSG %s :\x01ACTION %s\x01" % (self.chan, args))
        elif command == 'part':
            if self.ischan:
                self.connection.send("PART %s :%s" % (self.chan, args))
                self.ischan = False
                self.close()
        else:
            self.serverwin.cmd_handle(command, args)

_rfc_1459_command_regexp = re.compile("^(:(?P<prefix>[^ ]+) +)?(?P<command>[^ ]+)( *(?P<argument>.+))?")

class CustomInput(QtGui.QLineEdit):
    def __init__(self, p, parent=None):
        QtGui.QLineEdit.__init__(self, parent)
        self.parent = p

    cmdre = re.compile("/(?P<command>[^ ]+)(?: (?P<arguments>.+))?")

    def keyPressEvent(self, event):
        # For some reason, Qt.Key_Enter is wrong by one.
        if event.key() == Qt.Key_Enter-1:
            text = self.text()

            # Convert lines to the default command
            if text[0:2] == '//':
                text = '/say ' + text[1:]
            elif text[0:3] == '/ /':
                text = '/say ' + text[2:]
            if text[0] != '/':
                text = '/say ' + text

            m = self.cmdre.match(text)
            self.command.emit(m.group('command').lower(), m.group('arguments'))
            self.parent.inputField.setText("")
        else:
            QtGui.QLineEdit.keyPressEvent(self, event)

    command = QtCore.pyqtSignal(str, str)

if __name__ == "__main__":
    app = QtGui.QApplication([])
    widget = ServerWindow("Rizon")
    widget.show()
    widget.start()
    sys.exit(app.exec_())