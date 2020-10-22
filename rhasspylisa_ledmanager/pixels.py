
import time
import threading
from gpiozero import LED
try:
    import queue as Queue
except ImportError:
    import Queue as Queue

from .apa102 import APA102
from .led_patterns.alexa_led_pattern import AlexaLedPattern
from .led_patterns.google_home_led_pattern import GoogleHomeLedPattern

class Pixels:
	PIXELS_N = 12

	def __init__(self, pattern=AlexaLedPattern):
		self.pattern = pattern(show=self.show)
		self.queue = Queue.Queue()
		self.thread = threading.Thread(target=self._run)
		self.thread.daemon = True
		self.thread.start()

		self.last_direction = None

	def wakeup(self, direction=0):
		self.last_direction = direction
		def f():
			self.pattern.wakeup(direction)

		self.put(f)

	def listen(self):
		if self.last_direction:
			def f():
				self.pattern.wakeup(self.last_direction)
			self.put(f)
		else:
			self.put(self.pattern.listen)

	def think(self):
		self.put(self.pattern.think)

	def speak(self):
		self.put(self.pattern.speak)

	def off(self):
		self.put(self.pattern.off)

	def put(self, func):
		self.pattern.stop = True
		if self.queue.qsize() > 1:
			print('+-+-+-+- TOOOO MUCHHHH!!! (' + str(self.queue.qsize()) + ')')
		self.queue.put(func)

	def _run(self):
		while True:
			func = self.queue.get()
			self.pattern.stop = False
			func()

	def show(self, data):
		raise NotImplementedError


class Respeaker4MicArray(Pixels):
	PIXELS_N = 12

	def __init__(self, pattern=AlexaLedPattern, board_type=''):
		super().__init__(pattern=pattern)
		self.dev = APA102(num_led=self.PIXELS_N)
		self.power = LED(5)
		self.power.on()
		
	def show(self, data):
		for i in range(self.PIXELS_N):
			self.dev.set_pixel(i, int(data[4*i + 1]), int(data[4*i + 2]), int(data[4*i + 3]))
		self.dev.show()
		

# pixels = Pixels()

# Example
if __name__ == '__main__':
	
	pixels = Respeaker4MicArray()

	while True:

		try:
			pixels.wakeup()
			time.sleep(3)
			pixels.think()
			time.sleep(3)
			pixels.speak()
			time.sleep(6)
			pixels.off()
			time.sleep(3)
		except KeyboardInterrupt:
			break


	pixels.off()
	time.sleep(1)
