import sys
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt
from networkthread import *
from eventful import Eventful

class Connection(object):
  socket = None
  parent = None
  config = None
  commands = None
  net = None
  isConnected = False
  cmd_buffer = []
  
  def __init__(self, net, parent):
    self.config = Configuration()
    self.commands = Commands(self)
    self.net = net
    self.parent = parent
  
  def __del__(self):
    self.disconnect()
    del self.socket
  
  def connect(self):
    pass # Put in NetworkThread
  
  def disconnect(self, reason="Quitting"):
    self.commands.send_quit(reason)
    self.socket.close()
    self.isConnected = False
  
  def send_cmd(self, cmd):
    pass # Put in NetworkThread
  
  def parse_cmd(self, cmd):
    pass
  
  def register(self, nick):
    self.commands.send_user(nick)
    self.commands.send_nick(nick)
  
  def run(self):
    pass

class ParentLayout(QtGui.QWidget):
  """A debug layout for cuteIRC"""
  connection = None
  def __init__(self, parent=None):
    QtGui.QWidget.__init__(self, parent)
    
    self.setWindowTitle("cuteIRC")
    
    sendButton = QtGui.QPushButton("Send")
    
    self.inputField = CustomInput(self)
    
    self.chatArea = QtGui.QPlainTextEdit()
    self.chatArea.setTextInteractionFlags(Qt.TextInteractionFlag(5))
    
    grid = QtGui.QGridLayout()
    
    hbox = QtGui.QHBoxLayout()
    hbox.addWidget(self.inputField)
    hbox.addWidget(sendButton)
    
    vbox = QtGui.QVBoxLayout()
    vbox.addWidget(self.chatArea)
    vbox.addLayout(hbox)
    
    grid.addLayout(vbox,0,0)
    
    self.setLayout(grid)
    
    self.resize(350, 400)
  
  def start(self, net):
    self.connection = NetworkThread(self, net)
  
  @QtCore.pyqtSlot(str)
  def draw_text(self, text):
    self.chatArea.appendPlainText(text)
  
class CustomInput(QtGui.QLineEdit):
  def __init__(self, p, parent=None):
    QtGui.QLineEdit.__init__(self, parent)
    self.parent = p
  
  def keyPressEvent(self, event):
    # For some reason, Qt.Key_Enter is wrong by one.
    if event.key() == Qt.Key_Enter-1:
      self.parent.chatArea.appendPlainText(self.parent.inputField.text())
      self.parent.connection.send(self.parent.inputField.text()+"\r\n")
    else:
      QtGui.QLineEdit.keyPressEvent(self, event)

app = QtGui.QApplication([])
widget = ParentLayout()
widget.show()
widget.start("Rizon")
sys.exit(app.exec_())