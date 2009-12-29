class EventfulError(Exception):
	pass

class Eventful:
	def __init__(self, events=None):
		self._event_handlers = {}
		if events:
			self._events = events
	
	def add_events(self, *events):
		if not hasattr(self, "_events"):
			raise EventfulError("Either the Eventful instance is uninitialized, or a parent class that inherited Eventful did not define its events.")
		
		for event in events:
			if event in self._events:
				raise EventfulError("Attempted to add a duplicate event. (%s)" % event)
			
			self._events.append(event)
	
	def connect(self, event, function, *arguments, **named_arguments):
		if not hasattr(self, "_event_handlers"):
			self._event_handlers = ()
		
		if hasattr(self, "_events"):
			if not event in self._events:
				raise EventfulError("No such event '%s'." % event)
		
		if self.has_event_handler(event, function):
			self.disconnect(event, function)
		
		if not event in self._event_handlers:
			self._event_handlers[event] = []
		
		self._event_handlers[event].append({'function': function, 'arguments': arguments, 'named_arguments': named_arguments})
	
	def disconnect(self, event, function):
		if not hasattr(self, "_event_handlers"):
			raise EventfulError("Eventful instance was not initialized.")
		
		if hasattr(self, "_events"):
			if not event in self._events:
				raise EventfulError("No such event '%s'." % event)
		
		if event in self._event_handlers:
			for handler in self._event_handlers[event]:
				if handler['function'] == function:
					self._event_handlers.remove(handler)
					return
		
		raise EventfulError("No such event handler.")
	
	def eventful_emit(self, event, *arguments, **named_arguments):
		if not hasattr(self, "_event_handlers"):
			raise EventfulError("Eventful instance was not initialized.")
		
		if hasattr(self, "_events"):
			if not event in self._events:
				raise EventfulError("Attempted to emit a non-registered event. (%s)" % event)
		
		if hasattr(self, "_on_" + event):
			slot = getattr(self, "_on_" + event)
			slot(*arguments, **named_arguments)
		
		if event in self._event_handlers:
			for handler in self._event_handlers[event]:
				named_args = named_arguments.copy()
				named_args.update(handler['named_arguments'])
				handler['function'](*([self] + list(arguments) + list(handler['arguments'])), **named_args)
	
	def has_event_handler(self, event, function):
		if not hasattr(self, "_event_handlers"):
			raise EventfulError("Eventful instance was not initialized.")
		
		if hasattr(self, "_events"):
			if not event in self._events:
				raise EventfulError("No such event '%s'." % event)
		
		if self._event_handlers.has_key(event):
			for handler in self._event_handlers[event]:
				if handler['function'] == function:
					return True
		
		return False