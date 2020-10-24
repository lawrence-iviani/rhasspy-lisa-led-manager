from collections import namedtuple
from numpy import  arctan2, sqrt, sin , cos, pi, round, floor, rad2deg
import threading
from time import sleep

SpotEnergy = namedtuple('SpotEnergy', ['energy_plane_xy', 'energy_axis_z', 'level'])

#define ENERGY_COUNT 36
#struct led_energies_struct {
#	int energy_array_azimuth[ENERGY_COUNT]; // fi
#	int detect[ENERGY_COUNT]; //detection level (if present)
#};

DEFAULT_ENERGY_COUNT = 36 # should be a integer divisor of 360 (12,24,36,48,180 etc)


class base_sources:
	"""
	A base source handler, it provides the functionality to save a vector SpotEnergy, which describes the energy in one point
	"""
	def __init__(self, energy_count=DEFAULT_ENERGY_COUNT, callback=None):
		self.n_spots = energy_count
		self.callback = callback if callable(callback) else None
		self.energies = [SpotEnergy(energy_plane_xy=0.0,
									energy_axis_z=0.0,
									level=0.0) for l in range(energy_count)]
	
	def _update(self, e, x, y, z):
		r, elev, azimuth = calc_angles(x,y,z)
		azimuth = azimuth + pi #  Azimuth variates between -180,180 
		E_xy, E_z = calc_energies(e, elev, azimuth)
		spot_i = int( calc_spot_index(azimuth, self.n_spots)) #  self.n_spots//2 # if Azimuth variates between -180,180 need to shif the spot
		print('[{}] E[{:.3f},{:.3f},{:.3f}]-Rect({:.3f},{:.3f},{:.3f}) -> Pol({:.3f},{:.3f},{:.3f})'.format(spot_i, e, E_xy, E_z, x, y, z,r, rad2deg(elev), rad2deg(azimuth)))
		assert 0 <= spot_i < self.n_spots, "wrong spot: " + str(spot_i) + "-> 0:" + str(self.n_spots)
		# https://docs.python.org/3.8/library/collections.html#collections.somenamedtuple._replace
		self._decreas_all()
		self.energies[spot_i]=SpotEnergy(energy_plane_xy = E_xy, #_replace(energy_plane_xy = E_xy,
										 energy_axis_z = E_z,
										 level = e)
		if self.callback is not None:
			self.callback()

	def _decreas_all(self, fraction = 0.005):
		for n, spot in enumerate(self.energies):
			self.energies[n] = SpotEnergy(spot.energy_plane_xy*fraction, spot.energy_axis_z*fraction, spot.level*fraction)

	def reset_all(self):
		def _decreas_all_loop():
			for n in range(100):
				self.decrease_all(fraction=1.0/(n+10.0))
				sleep(0.002)
		threading.Thread(target=_decreas_all_loop,).start()# args=(1,))
		
		

class localized_sources(base_sources):
	"""Specialized class to convert a localized source in a basic source"""
	def update(self, data):
		x = data.x
		y = data.y
		z = data.z
		E = data.E
		
		self._update(E, x, y, z)
		# update energy count

	
class tracked_sources(base_sources):
	"""Specialized class to convert a tracked source in a basic source"""
	def update(self, data):
		x = data.x
		y = data.y
		z = data.z
		act = data.activity
		
		self._update(act, x, y, z)	
		# update energy count


def calc_angles(x,y,z):
	"""
	From a rectangular coordinates calc the spherical coordinates (r, θ, φ) in radians 
	as commonly used in physics (ISO 80000-2:2019 convention): 
	- radial distance r, The symbol ρ (rho) is often used instead of r. In our cases is always ~=1
	- polar angle θ (theta), inclination. The polar angle is often replaced by the elevation 
			angle measured (like in this case) from the reference plane, so that the elevation 
			angle of zero is at the horizon. The elevation angle is 90 degrees (π/2 radians) minus
			the inclination angle. 
	- azimuthal angle φ (phi). However, the azimuth φ is often restricted to the interval (−180°, +180°] , 
			or (−π, +π] in radians (like in this case),  instead of [0, 360°). 
			This is the standard convention for geographic longitude. 
	
	https://en.wikipedia.org/wiki/Spherical_coordinate_system#Coordinate_system_conversions
	"""
	XYsq = x**2 + y**2
	r = sqrt(XYsq + z**2)        	# r
	incli = arctan2(z,sqrt(XYsq)) 	# theta
	elev = pi/2.0 - incli 
	# TODO: it seems on the vector this has to be inverted...
	az = -arctan2(y,x)     	        # phi  
	return r, elev, az


def calc_energies(E, elevation, azimuth):
	"""
	Calculate the energiy of a syngol spot by getting the projection of E onto the plane xy and the axis z 
	This values represents the energy on the led plane and the elevation of the source on the axis z
	"""
	E_xy = E * sin(elevation)
	E_z = E * cos(elevation)
	return E_xy, E_z


def calc_spot_index(azimuth, n_spot, offset_spot=0):
	# azimuthal angle φ (phi). However, the azimuth φ is often restricted to the interval (−180°, +180°], 
	# or (−π, +π] in radians,  instead of [0, 360°). This is the standard convention for geographic longitude. 
	# Need to compensate the spot 0
	# compensate always to floor, this will fail only for azimuth equal to pi
	return offset_spot + floor(n_spot * azimuth/(2.0*pi))
	