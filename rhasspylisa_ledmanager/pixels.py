
import time
import threading

try:
    import queue as Queue
except ImportError:
    import Queue as Queue


# For Respeaker4MicArray
try: 
	from .apa102 import APA102
	from gpiozero import LED
except ImportError:
	print('Respeaker4MicArray seems unavailable or unistalled') 

# For MatrixVoice
try: 
	from matrix_lite import led as ev_led # ev: everloop
except ImportError:
	print('MatrixVoice seems unavailable or unistalled') 


	
class Pixels:
	
	def __init__(self, pattern, n_leds):
		self.pattern = pattern(show=self.show, number=n_leds)
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


class LedPattern:

	def __init__(self, number, show=None):
		self.pixels_number = number
		if not show or not callable(show):
			def dummy(data):
				pass
			show = dummy
		self.show = show
		self.stop = False

	def wakeup(self, direction=0):
		raise NotImplementedError

	def listen(self):
		raise NotImplementedError

	def think(self):
		raise NotImplementedError

	def speak(self):
		raise NotImplementedError

	def off(self):
		raise NotImplementedError


class Respeaker4MicArray(Pixels):
	PIXELS_N = 12

	def __init__(self, pattern):
		super().__init__(pattern=pattern, n_leds=PIXELS_N)
		self.dev = APA102(num_led=self.PIXELS_N)
		self.power = LED(5)
		self.power.on()
		
	def show(self, data):
		for i in range(self.PIXELS_N):
			self.dev.set_pixel(i, int(data[4*i + 1]), int(data[4*i + 2]), int(data[4*i + 3]))
		self.dev.show()


class MatrixVoice(Pixels):
	PIXELS_N = 0 # TODO

	def __init__(self, pattern):
		super().__init__(pattern=pattern, n_leds=ev_led.length )
		self.PIXELS_N = ev_led.length
		self.everloop_leds = ['black'] * self.PIXELS_N
		ev_led.set(self.everloop_leds)
		#self.dev = APA102(num_led=self.PIXELS_N)
		#self.power = LED(5)
		#self.power.on()
		
	def show(self, data):
		for i in range(self.PIXELS_N):
			# set r,g,b and white (always zero)
			self.everloop_leds[i] = (int(data[4*i + 1]), int(data[4*i + 2]), int(data[4*i + 3]), 0)
		ev_led.set(self.everloop_leds)


class DummyBoard(Pixels):

	def __init__(self, pattern):
		super().__init__(pattern=pattern(12))
		self.dev = 'Dummy'
		
	def show(self, data):
		pass
		

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
