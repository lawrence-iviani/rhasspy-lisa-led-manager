# Original from https://github.com/respeaker/4mics_hat

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


# Some definitons for LEDs
LED_MIN_VAL = 0
LED_MAX_VAL = 255
clamp_led = lambda n, minn, maxn: int(max(min(maxn, n), minn))
RESPEAKER_4MIC_ARRAY_N_LEDS = 12


class LedPattern:
	"""
	A class describing what a Led can do 
	"""
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
		

class Pixels:
	
	def __init__(self, pattern, n_leds):
		self.pattern = pattern(show=self.show, number=n_leds)
		self.queue = Queue.Queue()
		self.thread = threading.Thread(target=self._run)
		self.thread.daemon = True
		self.thread.start()
		self._led_buffer = [0,0,0,0] * n_leds # [not_sure, r,g,b]
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

	@property
	def pixels_number(self):
		return len(self._led_buffer)//4

	def set_all(self, list_rgb, persist_data=True, adding_policy='add'):
		# a flat list of length n_pixel*3 (r,g,b)
		# Get energy and combine
		data = [0,0,0,0] * self.pixels_number
		
		ratio = len(list_rgb)/self.pixels_number
		idxs = [int(n*ratio) for n in range(self.pixels_number)]
		
		# if the data has to be persisted stop the actual pattern in execution
		if persist_data:
			self.pattern.stop = True
			
		l_idx = idxs[0]
		for n,idx in enumerate(idxs[1:]):
			rgb = list_rgb[l_idx:idx]
			r = max([c[0] for c in rgb])
			g = max([c[1] for c in rgb])
			b = max([c[2] for c in rgb])
			
			data[n*4:(n+1)*4] = [0, r, g, b] # first element is always 0
			#data[n*4:(n+1)*4] = [0, rgb[0], rgb[1], rgb[2]] 
			l_idx = idx
		
		self.show(data, persist_data=persist_data, adding_policy=adding_policy)

	def _run(self):
		while True:
			func = self.queue.get()
			self.pattern.stop = False
			func()

	#def show(self, data, persist_data=True):
	#	raise NotImplementedError
	
	def show(self, data, persist_data=True, adding_policy='add'):
		"""
		Visualize the data array, a flat array that is interpreted in the follow way:
		cN_0..3: led N, color indexes: 0 not used, 1->r , 2->g, 3->b.
		[c0_0, c0_1, c0_2,c0_3, c1_0, c1_1, c1_2, c1_3, ... ]
		- persist_data: if True the data is save in the internal buffer and substitute the previous persited buffer
			if false, it is added with policy 
		- adding_policy: 'add'|'sub'|'min'|'max': add the value with persisted, 
			ubtract from data the persisted value,  or use min/max between data and persisted data
		 
		"""
		# move in main class
		if persist_data:
			self.ledbuffer = data # save the buffer
			for i in range(self.pixels_number):
				# set r,g,b and white (always zero)
				# become
				self.set_led(i , int(data[4*i + 1]), int(data[4*i + 2]), int(data[4*i + 3]))
				#self.everloop_leds[i] = (int(data[4*i + 1]), int(data[4*i + 2]), int(data[4*i + 3]), 0)
		else:
			data_set = [0,0,0]
			for i in range(self.pixels_number):				
				if adding_policy=='add':
					data_set[0] = self.ledbuffer[4*i+1] + data[4*i+1]
					data_set[1] = self.ledbuffer[4*i+2] + data[4*i+2]
					data_set[2] = self.ledbuffer[4*i+3] + data[4*i+3]
				elif adding_policy=='sub':
					data_set[0] = self.ledbuffer[4*i+1] - data[4*i+1]
					data_set[1] = self.ledbuffer[4*i+2] - data[4*i+2]
					data_set[2] = self.ledbuffer[4*i+3] - data[4*i+3]
				elif adding_policy=='max':
					data_set[0] = max(self.ledbuffer[4*i+1], data[4*i+1])
					data_set[1] = max(self.ledbuffer[4*i+2], data[4*i+2])
					data_set[2] = max(self.ledbuffer[4*i+3], data[4*i+3])
				elif adding_policy=='min':
					data_set[0] = min(self.ledbuffer[4*i+1], data[4*i+1])
					data_set[1] = min(self.ledbuffer[4*i+2], data[4*i+2])
					data_set[2] = min(self.ledbuffer[4*i+3], data[4*i+3])
				else:
					print(adding_policy)
					data_set[0] = self.ledbuffer[4*i+1] 
					data_set[1] = self.ledbuffer[4*i+2] 
					data_set[2] = self.ledbuffer[4*i+3] 
				# limit min,max value to an int
				# print(i, data_set[0], data_set[1], data_set[2])
				self.set_led(i, data_set[0], data_set[1], data_set[2])
		
		# update the entire LED strip
		self.update_leds()
		
	
	@property
	def ledbuffer(self):
		return self._led_buffer
	
	@ledbuffer.setter
	def ledbuffer(self, val):
		# TODO: check on input, list of multiple of 4 and conmpatible with the existing one
		self._led_buffer = val

	def set_led(i, r, g, b):
		raise NotImplementedError
		
	def update_leds():
		raise NotImplementedError
		


class Respeaker4MicArray(Pixels):

	def __init__(self, pattern):
		super().__init__(pattern=pattern, n_leds=RESPEAKER_4MIC_ARRAY_N_LEDS)
		self.dev = APA102(num_led=n_leds)
		self.power = LED(5)
		self.power.on()
		
	def set_led(self, i, r, g, b):
		if 0 <= i < self.pixels_number:
			 self.dev.set_pixel(i, r, g, b)
		else:
			print('Respeaker4MicArray: Index '+str(i)+' is out of range ')
		
	def update_leds(self):
		self.dev.show()


class MatrixVoice(Pixels):

	def __init__(self, pattern):
		super().__init__(pattern=pattern, n_leds=ev_led.length )
		# self.PIXELS_N = ev_led.length
		self._everloop_leds = ['black'] * self.pixels_number
		# ev_led.set(self.everloop_leds)
		self.update_leds()
		
	def set_led(self, i, r, g, b):
		#print(self.everloop_leds[i])
		if 0 <= i < ev_led.length:
			self._everloop_leds[i] = (int(r), int(g), int(b), 0)
		else:
			print('MatrixVoice: Index '+str(i)+' is out of range ')
		
	def update_leds(self):
		ev_led.set(self._everloop_leds)
	

class DummyBoard(Pixels):

	def __init__(self, pattern):
		super().__init__(pattern=pattern, n_leds=10)
		self.dev = 'Dummy'
		
	def set_led(self, i, r, g, b):
		pass
	
	def update_leds(self):
		pass


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
