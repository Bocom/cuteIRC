import yaml

class Configuration(object):
  config = None
  
  def __init__(self):
    if self.config is not None:
      return self.config
    else:
      self.open_config()
  
  def open_config(self):
    _file = open("configuration.conf", "r")
    self.config = yaml.load(_file)
    return self.config
  
  def save_config(self):
    _file = open("configuration.conf", "w")
    yaml.dump(self.config, _file)