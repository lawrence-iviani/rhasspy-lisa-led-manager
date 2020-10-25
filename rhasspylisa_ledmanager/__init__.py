"""Hermes MQTT server for Rhasspy Dialogue Mananger"""
import asyncio
import logging
import typing
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import threading
from time import sleep

from rhasspyhermes.asr import (
	AsrStartListening,
	AsrStopListening,
	AsrTextCaptured,
	AsrToggleOff,
	AsrToggleOn,
	AsrToggleReason,
)
from rhasspyhermes.audioserver import AudioPlayBytes, AudioPlayFinished
from rhasspyhermes.base import Message
from rhasspyhermes.client import GeneratorType, HermesClient, TopicArgs
from rhasspyhermes.dialogue import (
	DialogueAction,
	DialogueActionType,
	DialogueConfigure,
	DialogueContinueSession,
	DialogueEndSession,
	DialogueError,
	DialogueIntentNotRecognized,
	DialogueNotification,
	DialogueSessionEnded,
	DialogueSessionQueued,
	DialogueSessionStarted,
	DialogueSessionTermination,
	DialogueSessionTerminationReason,
	DialogueStartSession,
)
from rhasspyhermes.nlu import NluIntent, NluIntentNotRecognized, NluQuery
from rhasspyhermes.tts import TtsSay, TtsSayFinished
from rhasspyhermes.wake import (
	HotwordDetected,
	HotwordToggleOff,
	HotwordToggleOn,
	HotwordToggleReason,
)

# TODO: a mechanism for common storage of messages definition
# similar to https://github.com/rhasspy/rhasspy-hermes which contains all rhasspyhermes.xxx_messages
# Now is a link!!!
from lisa.rhasppy_messages import SSL_src_msg, SST_src_msg

from .utils import get_wav_duration

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.DEBUG)
_LOGGER = logging.getLogger("rhasspylisa_ledmanager")

# -----------------------------------------------------------------------------

StartSessionType = typing.Union[
	DialogueSessionStarted,
	DialogueSessionEnded,
	DialogueSessionQueued,
	AsrStartListening,
	AsrStopListening,
	HotwordToggleOff,
	DialogueError,
]

EndSessionType = typing.Union[
	DialogueSessionEnded,
	DialogueSessionStarted,
	DialogueSessionQueued,
	AsrStartListening,
	AsrStopListening,
	HotwordToggleOn,
	DialogueError,
]

SayType = typing.Union[
	TtsSay, AsrToggleOff, HotwordToggleOff, AsrToggleOn, HotwordToggleOn
]

SoundsType = typing.Union[
	typing.Tuple[AudioPlayBytes, TopicArgs],
	AsrToggleOff,
	HotwordToggleOff,
	AsrToggleOn,
	HotwordToggleOn,
]



# -----------------------------------------------------------------------------

# @dataclass
# class SessionInfo:
	# """Information for an active or queued dialogue session."""

	# session_id: str
	# site_id: str
	# start_session: DialogueStartSession
	# custom_data: typing.Optional[str] = None
	# intent_filter: typing.Optional[typing.List[str]] = None
	# send_intent_not_recognized: bool = False
	# continue_session: typing.Optional[DialogueContinueSession] = None
	# text_captured: typing.Optional[AsrTextCaptured] = None
	# step: int = 0
	# send_audio_captured: bool = True
	# lang: typing.Optional[str] = None

	# # Wake word that activated this session (if any)
	# detected: typing.Optional[HotwordDetected] = None
	# wakeword_id: str = ""




# -----------------------------------------------------------------------------

# pylint: disable=W0511
# TODO: Entity injection

from .pixels import Respeaker4MicArray, MatrixVoice, DummyBoard, LED_MIN_VAL, LED_MAX_VAL
from .led_patterns.google_home_led_pattern import GoogleHomeLedPattern
from .led_patterns.alexa_led_pattern import AlexaLedPattern
from .energy_DOAs import localized_sources, tracked_sources


defualt_pattern = 'GoogleHome'
available_hw = {'Respeaker4MicArray': Respeaker4MicArray,
				'MatrixVoice': MatrixVoice,
				'DummyBoard': DummyBoard,
				} #'': None}
available_led_patterns = {'GoogleHome': GoogleHomeLedPattern,
						  'Alexa': AlexaLedPattern,
					     } #'': None}				

				
class LedManagerHermesMqttException(Exception):
	pass


class LedManagerHermesMqtt(HermesClient): 
	"""Hermes MQTT server for Rhasspy Dialogue Manager."""

	def __init__(self,
				client,
				hw_led,
				pattern=None,
				site_ids: typing.Optional[typing.List[str]] = None,
	#       wakeword_ids: typing.Optional[typing.List[str]] = None,
	#       sound_paths: typing.Optional[typing.Dict[str, Path]] = None,
	#       session_timeout: float = 30.0,
	#       no_sound: typing.Optional[typing.List[str]] = None,
	):
		super().__init__("rhasspylisa_ledmanager", client, site_ids=site_ids)
		
		if pattern is None:
			_LOGGER.info("Using default pattern: " + str(defualt_pattern))
			pattern = defualt_pattern
		if hw_led in  available_hw:
			if pattern in available_led_patterns:
				self.pixels = available_hw[hw_led](pattern=available_led_patterns[pattern])  # available_hw[hw_led]# Respeaker4MicArray()
			else:
				self.pixels = available_hw[hw_led](pattern=available_led_patterns[defualt_pattern])
			_LOGGER.info("Loading hw: " + hw_led)
		else:
			_LOGGER.error("Hw board  " + hw_led + " not recognized, available " + str(available_hw.keys()))
			raise LedManagerHermesMqttException("Hw board not recognized: " + str(hw_led))
		
		self.tracked_energies = tracked_sources(callback=self.tracked_sources_update)
		self.localized_energies = localized_sources(callback=self.localized_sources_update)
		
		# Subscribe Hermese Protocol topics
		self.subscribe(
			#DialogueStartSession,
			DialogueSessionStarted,
			DialogueSessionEnded,
			DialogueSessionQueued,
			#DialogueContinueSession,
			#DialogueEndSession,
			#DialogueConfigure,
			TtsSayFinished,
			NluIntent,
			NluIntentNotRecognized,
			AsrTextCaptured,
			HotwordDetected,
			AudioPlayFinished,
		)
		
		# Subscribe Other MQTT messages topics{'lisa/': 	['ssl/source', 'sst/source'],}
		self.subscribe(SSL_src_msg, SST_src_msg)

	def localized_sources_update(self):
		# self.localized_energies
		# map the energy level in a vector of RGBs
		data_array_rgb = [[int(LED_MAX_VAL*e.energy_plane_xy), 0, 0] for e in self.localized_energies.energies]
		self.pixels.set_all(data_array_rgb, persist_data=False, adding_policy='add') # Avoid having priority with other visual messages (e.g. dialogue states)
		#print('tracked_sources_update: ' + str(data_array_rgb))
	
	def tracked_sources_update(self):
		# self.tracked_energies
		# map the energy level in a vector of RGBs
		data_array_rgb = [[0, int(LED_MAX_VAL*e.energy_axis_z), int(LED_MAX_VAL*e.energy_plane_xy)] for e in self.tracked_energies.energies]
		self.pixels.set_all(data_array_rgb, persist_data=False, adding_policy='max') # Avoid having priority with other visual messages (e.g. dialogue states)
		#print('tracked_sources_update: '+ str(data_array_rgb)) 
		
	# -------------------------------------------------------------------------

	@staticmethod
	def get_available_hw():
		return available_hw.keys()

	@staticmethod
	def get_available_patterns():
		return available_led_patterns.keys()

	# TODO: check all site_ids, reply should be only for the site id specified 
	def wakeup(self):
		_LOGGER.debug("enter wakeup")
		self.pixels.off()
		self.pixels.wakeup()
		# sleep(1)
		# self.pixels.off()
		_LOGGER.debug("exit wakeup")

	def speak(self):
		_LOGGER.debug("enter speak")
		self.pixels.off()
		self.pixels.speak()
		_LOGGER.debug("exit speak")
		
	def end_speak(self):
		_LOGGER.debug("enter end_speak")
		self.pixels.off()
		_LOGGER.debug("exit end_speak")
		
	def think(self):
		_LOGGER.debug("enter think")
		self.pixels.off()
		self.pixels.think()
		_LOGGER.debug("exit think")

	def not_recognized(self):
		_LOGGER.debug("enter not_recognized")
		self.pixels.off()
		_LOGGER.debug("exit not_recognized")
	
	def recognized(self):
		_LOGGER.debug("enter recognized")
		self.pixels.listen()
		_LOGGER.debug("exit recognized")

	async def on_message(
		self,
		message: Message,
		site_id: typing.Optional[str] = None,
		session_id: typing.Optional[str] = None,
		topic: typing.Optional[str] = None,
	) -> GeneratorType:
		# _LOGGER.debug("{}: {}".format(type(message), message))
		if isinstance(message, SSL_src_msg ):
			self.localized_energies.update(message)
			pass# threading.Thread(target=self.speak,).start()# args=(1,))
		elif isinstance(message, SST_src_msg):
			self.tracked_energies.update(message)
			pass# threading.Thread(target=self.speak,).start()# args=(1,))
		elif isinstance(message, AsrTextCaptured):
			_LOGGER.debug("AsrTextCaptured: {}".format(message))
			threading.Thread(target=self.think,).start()# args=(1,))

		elif isinstance(message, AudioPlayFinished):
			# Audio output finished
			# play_finished_event = self.message_events[AudioPlayFinished].get(message.id)
			_LOGGER.debug("AudioPlayFinished: {}".format(message))
			# if play_finished_event:
				# play_finished_event.set()
		elif isinstance(message, DialogueConfigure):
			_LOGGER.debug("DialogueConfigure: {}".format(message))
			# Configure intent filter
			# self.handle_configure(message)
		# elif isinstance(message, DialogueStartSession):
		elif isinstance(message, DialogueSessionStarted):
			_LOGGER.debug("DialogueSessionStarted: {}".format(message))
			threading.Thread(target=self.speak,).start()# args=(1,))
			
			# Start session
			# async for start_result in self.handle_start(message):
				# yield start_result
		elif isinstance(message, DialogueSessionEnded):
			_LOGGER.debug("DialogueSessionEnded: {}".format(message))
			threading.Thread(target=self.end_speak,).start()# args=(1,))
			
			# Start session
			# async for start_result in self.handle_start(message):
				# yield start_result
		elif isinstance(message, DialogueContinueSession):
			_LOGGER.debug("DialogueContinueSession: {}".format(message))
			# Continue session
			# async for continue_result in self.handle_continue(message):
				# yield continue_result
		elif isinstance(message, DialogueEndSession):
			_LOGGER.debug("DialogueEndSession: {}".format(message))
			# self.pixels.off()
			# End session
			# async for end_result in self.handle_end(message):
				# yield end_result
		elif isinstance(message, HotwordDetected):
			_LOGGER.debug("HotwordDetected: {}".format(message))
			threading.Thread(target=self.wakeup,).start()# args=(1,))
			# Wakeword detected
			# assert topic, "Missing topic"
			# wakeword_id = HotwordDetected.get_wakeword_id(topic)
			# if (not self.wakeword_ids) or (wakeword_id in self.wakeword_ids):
				# async for wake_result in self.handle_wake(wakeword_id, message):
					# yield wake_result
			# else:
				# _LOGGER.warning("Ignoring wake word id=%s", wakeword_id)
		elif isinstance(message, NluIntent):
			_LOGGER.debug("NluIntent: {}".format(message))
			threading.Thread(target=self.recognized,).start()# args=(1,))
			# Intent recognized
			# await self.handle_recognized(message)
		elif isinstance(message, NluIntentNotRecognized):
			_LOGGER.debug("NluIntentNotRecognized: {}".format(message))
			threading.Thread(target=self.not_recognized,).start()# args=(1,))
			# Intent not recognized
			# async for play_error_result in self.maybe_play_sound(
				# "error", site_id=message.site_id
			# ):
				# yield play_error_result

			# async for not_recognized_result in self.handle_not_recognized(message):
				# yield not_recognized_result
		elif isinstance(message, TtsSayFinished):
			_LOGGER.debug("TtsSayFinished: {}".format(message))
			# Text to speech finished
			# say_finished_event = self.message_events[TtsSayFinished].pop(
				# message.id, None
			# )
			# if say_finished_event:
				# say_finished_event.set()
		else:
			_LOGGER.warning("Unexpected message: %s", message)
			
		yield
    # -------------------------------------------------------------------------
