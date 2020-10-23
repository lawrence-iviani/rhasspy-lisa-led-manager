"""Hermes MQTT server for Rhasspy Dialogue Mananger"""
import asyncio
import logging
import typing
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

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

from .utils import get_wav_duration

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

import threading
from time import sleep

# -----------------------------------------------------------------------------

@dataclass
class SessionInfo:
	"""Information for an active or queued dialogue session."""

	session_id: str
	site_id: str
	start_session: DialogueStartSession
	custom_data: typing.Optional[str] = None
	intent_filter: typing.Optional[typing.List[str]] = None
	send_intent_not_recognized: bool = False
	continue_session: typing.Optional[DialogueContinueSession] = None
	text_captured: typing.Optional[AsrTextCaptured] = None
	step: int = 0
	send_audio_captured: bool = True
	lang: typing.Optional[str] = None

	# Wake word that activated this session (if any)
	detected: typing.Optional[HotwordDetected] = None
	wakeword_id: str = ""


# -----------------------------------------------------------------------------

# pylint: disable=W0511
# TODO: Entity injection

from .pixels import Respeaker4MicArray, MatrixVoice, DummyBoard
from .pixels import Respeaker4MicArray, MatrixVoice, DummyBoard
from .led_patterns.google_home_led_pattern import GoogleHomeLedPattern
from .led_patterns.alexa_led_pattern import AlexaLedPattern

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
		# sleep(5)
		# self.pixels.off()
		_LOGGER.debug("exit speak")
		
	def end_speak(self):
		_LOGGER.debug("enter end_speak")
		self.pixels.off()
		# sleep(0.1)
		# for i in range(5):
			# self.pixels.speak()
			# sleep(0.1)
			# self.pixels.off()
			# sleep(0.1)
		# self.pixels.off()
		_LOGGER.debug("exit end_speak")
		
	def think(self):
		_LOGGER.debug("enter think")
		self.pixels.off()
		self.pixels.think()
		# for i in range(2):
			# self.pixels.think()
			# sleep(0.5)
			# self.pixels.off()
			# sleep(0.5)
		_LOGGER.debug("exit think")

	def not_recognized(self):
		_LOGGER.debug("enter not_recognized")
		self.pixels.off()
		# for i in range(5):
			# self.pixels.think()
			# sleep(0.25)
			# self.pixels.off()
			# sleep(0.25)
		_LOGGER.debug("exit not_recognized")
	
	def recognized(self):
		_LOGGER.debug("enter recognized")
#		self.pixels.off()
		self.pixels.listen()
		# sleep(0.25)
		# self.pixels.speak()
		# sleep(0.25)
		# self.pixels.off()
		_LOGGER.debug("exit recognized")

	async def on_message(
		self,
		message: Message,
		site_id: typing.Optional[str] = None,
		session_id: typing.Optional[str] = None,
		topic: typing.Optional[str] = None,
	) -> GeneratorType:
		# _LOGGER.debug("{}: {}".format(type(message), message))
		if isinstance(message, AsrTextCaptured):
			_LOGGER.debug("AsrTextCaptured: {}".format(message))
			threading.Thread(target=self.think,).start()# args=(1,))
			
			# ASR transcription received
			# if (not message.session_id) or (
				# not self.valid_session_id(message.session_id)
			# ):
				# _LOGGER.warning("Ignoring unknown session %s", message.session_id)
				# return

			# async for play_recorded_result in self.maybe_play_sound(
				# "recorded", site_id=message.site_id
			# ):
				# yield play_recorded_result

			# async for text_result in self.handle_text_captured(message):
				# yield text_result

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
    # async def handle_start(
        # self, start_session: DialogueStartSession
    # ) -> typing.AsyncIterable[typing.Union[StartSessionType, EndSessionType, SayType]]:
        # """Starts or queues a new dialogue session."""
        # try:
            # session_id = str(uuid4())
            # new_session = SessionInfo(
                # session_id=session_id,
                # site_id=start_session.site_id,
                # start_session=start_session,
            # )

            # async for start_result in self.start_session(new_session):
                # yield start_result
        # except Exception as e:
            # _LOGGER.exception("handle_start")
            # yield DialogueError(
                # error=str(e), context=str(start_session), site_id=start_session.site_id
            # )

    # async def start_session(
        # self, new_session: SessionInfo
    # ) -> typing.AsyncIterable[typing.Union[StartSessionType, EndSessionType, SayType]]:
        # """Start a new session."""
        # start_session = new_session.start_session
        # site_session = self.session_by_site.get(new_session.site_id)

        # if start_session.init.type == DialogueActionType.NOTIFICATION:
            # # Notification session
            # notification = start_session.init
            # assert isinstance(
                # notification, DialogueNotification
            # ), "Not a DialogueNotification"

            # if not site_session:
                # # Create new session just for TTS
                # _LOGGER.debug("Starting new session (id=%s)", new_session.session_id)
                # self.all_sessions[new_session.session_id] = new_session
                # self.session_by_site[new_session.site_id] = new_session

                # yield DialogueSessionStarted(
                    # site_id=new_session.site_id,
                    # session_id=new_session.session_id,
                    # custom_data=new_session.custom_data,
                    # lang=new_session.lang,
                # )

                # site_session = new_session

            # if notification.text:
                # async for say_result in self.say(
                    # notification.text,
                    # site_id=site_session.site_id,
                    # session_id=site_session.session_id,
                # ):
                    # yield say_result

            # # End notification session immedately
            # _LOGGER.debug("Session ended nominally: %s", site_session.session_id)
            # async for end_result in self.end_session(
                # DialogueSessionTerminationReason.NOMINAL,
                # site_id=site_session.site_id,
                # session_id=site_session.session_id,
                # start_next_session=True,
            # ):
                # yield end_result
        # else:
            # # Action session
            # action = start_session.init
            # assert isinstance(action, DialogueAction), "Not a DialogueAction"

            # new_session.custom_data = start_session.custom_data
            # new_session.intent_filter = action.intent_filter
            # new_session.send_intent_not_recognized = action.send_intent_not_recognized

            # start_new_session = True

            # if site_session:
                # if action.can_be_enqueued:
                    # # Queue session for later
                    # session_queue = self.session_queue_by_site[new_session.site_id]

                    # start_new_session = False
                    # session_queue.append(new_session)

                    # yield DialogueSessionQueued(
                        # session_id=new_session.session_id,
                        # site_id=new_session.site_id,
                        # custom_data=new_session.custom_data,
                    # )
                # else:
                    # # Abort existing session
                    # _LOGGER.debug("Session aborted: %s", site_session.session_id)
                    # async for end_result in self.end_session(
                        # DialogueSessionTerminationReason.ABORTED_BY_USER,
                        # site_id=site_session.site_id,
                        # session_id=site_session.session_id,
                        # start_next_session=False,
                    # ):
                        # yield end_result

            # if start_new_session:
                # # Start new session
                # _LOGGER.debug("Starting new session (id=%s)", new_session.session_id)
                # self.all_sessions[new_session.session_id] = new_session
                # self.session_by_site[new_session.site_id] = new_session

                # yield DialogueSessionStarted(
                    # site_id=new_session.site_id,
                    # session_id=new_session.session_id,
                    # custom_data=new_session.custom_data,
                    # lang=new_session.lang,
                # )

                # # Disable hotword for session
                # yield HotwordToggleOff(
                    # site_id=new_session.site_id,
                    # reason=HotwordToggleReason.DIALOGUE_SESSION,
                # )

                # if action.text:
                    # # Forward to TTS
                    # async for say_result in self.say(
                        # action.text,
                        # site_id=new_session.site_id,
                        # session_id=new_session.session_id,
                    # ):
                        # yield say_result

                # # Start ASR listening
                # _LOGGER.debug("Listening for session %s", new_session.session_id)
                # if (
                    # new_session.detected
                    # and new_session.detected.send_audio_captured is not None
                # ):
                    # # Use setting from hotword detection
                    # new_session.send_audio_captured = (
                        # new_session.detected.send_audio_captured
                    # )

                # yield AsrStartListening(
                    # site_id=new_session.site_id,
                    # session_id=new_session.session_id,
                    # send_audio_captured=new_session.send_audio_captured,
                    # wakeword_id=new_session.wakeword_id,
                    # lang=new_session.lang,
                # )

                # # Set up timeout
                # asyncio.create_task(
                    # self.handle_session_timeout(
                        # new_session.site_id, new_session.session_id, new_session.step
                    # )
                # )

    # async def handle_continue(
        # self, continue_session: DialogueContinueSession
    # ) -> typing.AsyncIterable[
        # typing.Union[AsrStartListening, AsrStopListening, SayType, DialogueError]
    # ]:
        # """Continue the existing session."""
        # site_session = self.all_sessions.get(continue_session.session_id)

        # if site_session is None:
            # _LOGGER.warning(
                # "No session for id %s. Cannot continue.", continue_session.session_id
            # )
            # return

        # try:
            # if continue_session.custom_data is not None:
                # # Overwrite custom data
                # site_session.custom_data = continue_session.custom_data

            # if continue_session.lang is not None:
                # # Overwrite language
                # site_session.lang = continue_session.lang

            # site_session.intent_filter = continue_session.intent_filter

            # site_session.send_intent_not_recognized = (
                # continue_session.send_intent_not_recognized
            # )

            # site_session.step += 1

            # _LOGGER.debug(
                # "Continuing session %s (step=%s)",
                # site_session.session_id,
                # site_session.step,
            # )

            # # Stop listening
            # yield AsrStopListening(
                # site_id=site_session.site_id, session_id=site_session.session_id
            # )

            # # Ensure hotword is disabled for session
            # yield HotwordToggleOff(
                # site_id=site_session.site_id,
                # reason=HotwordToggleReason.DIALOGUE_SESSION,
            # )

            # if continue_session.text:
                # # Forward to TTS
                # async for tts_result in self.say(
                    # continue_session.text,
                    # site_id=site_session.site_id,
                    # session_id=continue_session.session_id,
                # ):
                    # yield tts_result

            # # Start ASR listening
            # _LOGGER.debug("Listening for session %s", site_session.session_id)
            # yield AsrStartListening(
                # site_id=site_session.site_id,
                # session_id=site_session.session_id,
                # send_audio_captured=site_session.send_audio_captured,
                # lang=site_session.lang,
            # )

            # # Set up timeout
            # asyncio.create_task(
                # self.handle_session_timeout(
                    # site_session.site_id, site_session.session_id, site_session.step
                # )
            # )

        # except Exception as e:
            # _LOGGER.exception("handle_continue")
            # yield DialogueError(
                # error=str(e),
                # context=str(continue_session),
                # site_id=site_session.site_id,
                # session_id=continue_session.session_id,
            # )

    # async def handle_end(
        # self, end_session: DialogueEndSession
    # ) -> typing.AsyncIterable[typing.Union[EndSessionType, StartSessionType, SayType]]:
        # """End the current session."""
        # site_session = self.all_sessions.get(end_session.session_id)
        # if not site_session:
            # _LOGGER.warning("No session for id %s. Cannot end.", end_session.session_id)
            # return

        # try:
            # # Say text before ending session
            # if end_session.text:
                # # Forward to TTS
                # async for tts_result in self.say(
                    # end_session.text,
                    # site_id=site_session.site_id,
                    # session_id=end_session.session_id,
                # ):
                    # yield tts_result

            # # Update fields
            # if end_session.custom_data is not None:
                # site_session.custom_data = end_session.custom_data

            # _LOGGER.debug("Session ended nominally: %s", site_session.session_id)
            # async for end_result in self.end_session(
                # DialogueSessionTerminationReason.NOMINAL,
                # site_id=site_session.site_id,
                # session_id=site_session.session_id,
                # start_next_session=True,
            # ):
                # yield end_result
        # except Exception as e:
            # _LOGGER.exception("handle_end")
            # yield DialogueError(
                # error=str(e),
                # context=str(end_session),
                # site_id=site_session.site_id,
                # session_id=end_session.session_id,
            # )

            # # Enable hotword on error
            # yield HotwordToggleOn(
                # site_id=site_session.site_id,
                # reason=HotwordToggleReason.DIALOGUE_SESSION,
            # )

    # async def end_session(
        # self,
        # reason: DialogueSessionTerminationReason,
        # site_id: str,
        # session_id: str,
        # start_next_session: bool,
    # ) -> typing.AsyncIterable[typing.Union[EndSessionType, StartSessionType, SayType]]:
        # """End current session and start queued session."""
        # site_session = self.all_sessions.pop(session_id, None)
        # if site_session:
            # # End the existing session
            # if site_session.start_session.init.type != DialogueActionType.NOTIFICATION:
                # # Stop listening
                # yield AsrStopListening(
                    # site_id=site_session.site_id, session_id=site_session.session_id
                # )

            # yield DialogueSessionEnded(
                # site_id=site_id,
                # session_id=site_session.session_id,
                # custom_data=site_session.custom_data,
                # termination=DialogueSessionTermination(reason=reason),
            # )
        # else:
            # _LOGGER.warning("No session for id %s", session_id)

        # # Check session queue
        # session_queue = self.session_queue_by_site[site_id]
        # if session_queue:
            # if start_next_session:
                # _LOGGER.debug("Handling queued session")
                # async for start_result in self.start_session(session_queue.popleft()):
                    # yield start_result
        # else:
            # # Enable hotword if no queued sessions
            # yield HotwordToggleOn(
                # site_id=site_id, reason=HotwordToggleReason.DIALOGUE_SESSION
            # )

    # async def handle_text_captured(
        # self, text_captured: AsrTextCaptured
    # ) -> typing.AsyncIterable[
        # typing.Union[AsrStopListening, HotwordToggleOn, NluQuery]
    # ]:
        # """Handle ASR text captured for session."""
        # try:
            # if not text_captured.session_id:
                # _LOGGER.warning("Missing session id on text captured message.")
                # return

            # site_session = self.all_sessions.get(text_captured.session_id)
            # if site_session is None:
                # _LOGGER.warning(
                    # "No session for id %s. Dropping captured text from ASR.",
                    # text_captured.session_id,
                # )
                # return

            # _LOGGER.debug("Received text: %s", text_captured.text)

            # # Record result
            # site_session.text_captured = text_captured

            # # Stop listening
            # yield AsrStopListening(
                # site_id=text_captured.site_id, session_id=site_session.session_id
            # )

            # # Enable hotword
            # yield HotwordToggleOn(
                # site_id=text_captured.site_id,
                # reason=HotwordToggleReason.DIALOGUE_SESSION,
            # )

            # # Perform query
            # yield NluQuery(
                # input=text_captured.text,
                # intent_filter=site_session.intent_filter or self.default_intent_filter,
                # session_id=site_session.session_id,
                # site_id=site_session.site_id,
                # wakeword_id=text_captured.wakeword_id or site_session.wakeword_id,
                # lang=text_captured.lang or site_session.lang,
            # )
        # except Exception:
            # _LOGGER.exception("handle_text_captured")

    # async def handle_recognized(self, recognition: NluIntent) -> None:
        # """Intent successfully recognized."""
        # try:
            # if not recognition.session_id:
                # _LOGGER.warning("Missing session id on intent message.")
                # return

            # site_session = self.all_sessions.get(recognition.session_id)
            # if site_session is None:
                # _LOGGER.warning(
                    # "No session for id %s. Dropping recognition.",
                    # recognition.session_id,
                # )
                # return

            # _LOGGER.debug("Recognized %s", recognition)
        # except Exception:
            # _LOGGER.exception("handle_recognized")

    # async def handle_not_recognized(
        # self, not_recognized: NluIntentNotRecognized
    # ) -> typing.AsyncIterable[
        # typing.Union[
            # DialogueIntentNotRecognized, EndSessionType, StartSessionType, SayType
        # ]
    # ]:
        # """Failed to recognized intent."""
        # try:
            # if not not_recognized.session_id:
                # _LOGGER.debug("Missing session id on not recognized message")
                # return

            # site_session = self.all_sessions.get(not_recognized.session_id)

            # if site_session is None:
                # _LOGGER.warning(
                    # "No session for id %s. Dropping not recognized.",
                    # not_recognized.session_id,
                # )
                # return

            # if not_recognized.custom_data is not None:
                # # Overwrite custom data
                # site_session.custom_data = not_recognized.custom_data

            # _LOGGER.warning(
                # "No intent recognized (site_id=%s, session_id=%s)",
                # not_recognized.site_id,
                # not_recognized.session_id,
            # )

            # if site_session.send_intent_not_recognized:
                # # Client will handle
                # yield DialogueIntentNotRecognized(
                    # session_id=site_session.session_id,
                    # custom_data=site_session.custom_data,
                    # site_id=not_recognized.site_id,
                    # input=not_recognized.input,
                # )
            # else:
                # # End session automatically
                # async for end_result in self.end_session(
                    # DialogueSessionTerminationReason.INTENT_NOT_RECOGNIZED,
                    # site_id=not_recognized.site_id,
                    # session_id=not_recognized.session_id,
                    # start_next_session=True,
                # ):
                    # yield end_result
        # except Exception:
            # _LOGGER.exception("handle_not_recognized")

    # async def handle_wake(
        # self, wakeword_id: str, detected: HotwordDetected
    # ) -> typing.AsyncIterable[
        # typing.Union[EndSessionType, StartSessionType, SayType, SoundsType]
    # ]:
        # """Wake word was detected."""
        # try:
            # session_id = (
                # detected.session_id or f"{detected.site_id}-{wakeword_id}-{uuid4()}"
            # )
            # new_session = SessionInfo(
                # session_id=session_id,
                # site_id=detected.site_id,
                # start_session=DialogueStartSession(
                    # site_id=detected.site_id,
                    # custom_data=wakeword_id,
                    # init=DialogueAction(can_be_enqueued=False),
                # ),
                # detected=detected,
                # wakeword_id=wakeword_id,
                # lang=detected.lang,
            # )

            # # Play wake sound before ASR starts listening
            # async for play_wake_result in self.maybe_play_sound(
                # "wake", site_id=detected.site_id
            # ):
                # yield play_wake_result

            # site_session = self.session_by_site.get(detected.site_id)
            # if site_session:
                # # Jump the queue
                # self.session_queue_by_site[site_session.site_id].appendleft(new_session)

                # # Abort previous session and start queued session
                # async for end_result in self.end_session(
                    # DialogueSessionTerminationReason.ABORTED_BY_USER,
                    # site_id=site_session.site_id,
                    # session_id=site_session.session_id,
                    # start_next_session=True,
                # ):
                    # yield end_result
            # else:
                # # Start new session
                # async for start_result in self.start_session(new_session):
                    # yield start_result
        # except Exception as e:
            # _LOGGER.exception("handle_wake")
            # yield DialogueError(
                # error=str(e), context=str(detected), site_id=detected.site_id
            # )

    # async def handle_session_timeout(self, site_id: str, session_id: str, step: int):
        # """Called when a session has timed out."""
        # try:
            # # Pause execution until timeout
            # await asyncio.sleep(self.session_timeout)

            # # Check if we're still on the same session and step (i.e., no continues)

            # site_session = self.all_sessions.get(session_id)

            # if (
                # site_session
                # and (site_session.site_id == site_id)
                # and (site_session.step == step)
            # ):
                # _LOGGER.error("Session timed out for site %s: %s", site_id, session_id)

                # # Abort session
                # await self.publish_all(
                    # self.end_session(
                        # DialogueSessionTerminationReason.TIMEOUT,
                        # site_id=site_id,
                        # session_id=session_id,
                        # start_next_session=True,
                    # )
                # )
        # except Exception as e:
            # _LOGGER.exception("session_timeout")
            # self.publish(
                # DialogueError(
                    # error=str(e),
                    # context="session_timeout",
                    # site_id=site_id,
                    # session_id=session_id,
                # )
            # )

    # def handle_configure(self, configure: DialogueConfigure):
        # """Set default intent filter."""
        # self.default_intent_filter = [
            # intent.intent_id for intent in configure.intents if intent.enable
        # ]

        # if self.default_intent_filter:
            # _LOGGER.debug("Default intent filter set: %s", self.default_intent_filter)
        # else:
            # self.default_intent_filter = None
            # _LOGGER.debug("Removed default intent filter")

    # -------------------------------------------------------------------------


    # async def say(
        # self,
        # text: str,
        # site_id="default",
        # session_id="",
        # request_id: typing.Optional[str] = None,
        # block: bool = True,
    # ) -> typing.AsyncIterable[
        # typing.Union[
            # TtsSay, HotwordToggleOn, HotwordToggleOff, AsrToggleOn, AsrToggleOff
        # ]
    # ]:
        # """Send text to TTS system and wait for reply."""
        # finished_event = asyncio.Event()
        # finished_id = request_id or str(uuid4())
        # self.message_events[TtsSayFinished][finished_id] = finished_event

        # # Disable ASR/hotword at site
        # yield HotwordToggleOff(site_id=site_id, reason=HotwordToggleReason.TTS_SAY)
        # yield AsrToggleOff(site_id=site_id, reason=AsrToggleReason.TTS_SAY)

        # # Wait for messages to be delivered
        # await asyncio.sleep(self.toggle_delay)

        # try:
            # # Forward to TTS
            # _LOGGER.debug("Say: %s", text)
            # yield TtsSay(
                # id=finished_id, site_id=site_id, session_id=session_id, text=text
            # )

            # if block:
                # # Wait for finished event
                # _LOGGER.debug(
                    # "Waiting for sayFinished (id=%s, timeout=%s)",
                    # finished_id,
                    # self.say_finished_timeout,
                # )
                # await asyncio.wait_for(
                    # finished_event.wait(), timeout=self.say_finished_timeout
                # )
        # except asyncio.TimeoutError:
            # _LOGGER.warning("Did not receive sayFinished before timeout")
        # except Exception:
            # _LOGGER.exception("say")
        # finally:
            # # Wait for audio to finish play
            # await asyncio.sleep(self.toggle_delay)

            # # Re-enable ASR/hotword at site
            # yield HotwordToggleOn(site_id=site_id, reason=HotwordToggleReason.TTS_SAY)
            # yield AsrToggleOn(site_id=site_id, reason=AsrToggleReason.TTS_SAY)

    # -------------------------------------------------------------------------

    # async def maybe_play_sound(
        # self,
        # sound_name: str,
        # site_id: typing.Optional[str] = None,
        # request_id: typing.Optional[str] = None,
        # block: bool = True,
    # ) -> typing.AsyncIterable[SoundsType]:
        # """Play WAV sound through audio out if it exists."""
        # if site_id in self.no_sound:
            # _LOGGER.debug("Sound is disabled for site %s", site_id)
            # return

        # site_id = site_id or self.site_id
        # wav_path = self.sound_paths.get(sound_name)
        # if wav_path:
            # if not wav_path.is_file():
                # _LOGGER.error("WAV does not exist: %s", str(wav_path))
                # return

            # _LOGGER.debug("Playing WAV %s", str(wav_path))
            # wav_bytes = wav_path.read_bytes()

            # request_id = request_id or str(uuid4())
            # finished_event = asyncio.Event()
            # finished_id = request_id
            # self.message_events[AudioPlayFinished][finished_id] = finished_event

            # # Disable ASR/hotword at site
            # yield HotwordToggleOff(
                # site_id=site_id, reason=HotwordToggleReason.PLAY_AUDIO
            # )
            # yield AsrToggleOff(site_id=site_id, reason=AsrToggleReason.PLAY_AUDIO)

            # # Wait for messages to be delivered
            # await asyncio.sleep(self.toggle_delay)

            # try:
                # yield (
                    # AudioPlayBytes(wav_bytes=wav_bytes),
                    # {"site_id": site_id, "request_id": request_id},
                # )

                # # Wait for finished event or WAV duration
                # if block:
                    # wav_duration = get_wav_duration(wav_bytes)
                    # wav_timeout = wav_duration + self.sound_timeout_extra
                    # _LOGGER.debug(
                        # "Waiting for playFinished (id=%s, timeout=%s)",
                        # finished_id,
                        # wav_timeout,
                    # )
                    # await asyncio.wait_for(finished_event.wait(), timeout=wav_timeout)
            # except asyncio.TimeoutError:
                # _LOGGER.warning("Did not receive sayFinished before timeout")
            # except Exception:
                # _LOGGER.exception("maybe_play_sound")
            # finally:
                # # Wait for audio to finish playing
                # await asyncio.sleep(self.toggle_delay)

                # # Re-enable ASR/hotword at site
                # yield HotwordToggleOn(
                    # site_id=site_id, reason=HotwordToggleReason.PLAY_AUDIO
                # )
                # yield AsrToggleOn(site_id=site_id, reason=AsrToggleReason.PLAY_AUDIO)

    # # -------------------------------------------------------------------------

    # def valid_session_id(self, session_id: str) -> bool:
        # """True if payload session_id matches current session_id."""
        # return session_id in self.all_sessions
