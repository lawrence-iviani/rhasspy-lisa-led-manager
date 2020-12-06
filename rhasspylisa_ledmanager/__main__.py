"""Forked witbh a differnt scope From """
"""Hermes MQTT dialogue manager for Rhasspy"""
import argparse
import asyncio
import logging
import typing
from pathlib import Path

import paho.mqtt.client as mqtt
import rhasspyhermes.cli as hermes_cli

from . import LedManagerHermesMqtt, LedManagerHermesMqttException

_LOGGER = logging.getLogger("rhasspylisa_ledmanager")

# -----------------------------------------------------------------------------
def main():
	"""Main method."""
	hw_board = 'DummyBoard'
	led_pattern = 'GoogleHome'
	
	parser = argparse.ArgumentParser(prog="rhasspy-lisa-led-manager")
	parser.add_argument("--hw-board", 
						nargs='?', default=hw_board, const=hw_board, 
						help="Select one supported board between: " + str(LedManagerHermesMqtt.get_available_hw())+ ', default is: ' + hw_board,)
	parser.add_argument("--led-pattern", 
						nargs='?', default=led_pattern, const=led_pattern, 
						help="Select one led pattern: " + str(LedManagerHermesMqtt.get_available_patterns())+ ', default is: ' + led_pattern,)
	# parser.add_argument(
		# "--hw-led",
		# action="append",
		# help="Select one supported board between: " + str(LedManagerHermesMqtt.get_available_hw()),
	# )
	# parser.add_argument(
		# "--session-timeout",
		# type=float,
		# default=30.0,
		# help="Seconds before a dialogue session times out (default: 30)",
	# )
	# parser.add_argument("--sound", nargs=2, action="append", help="Add WAV id/path")
	# parser.add_argument(
		# "--no-sound", action="append", help="Disable notification sounds for site id"
	# )

	hermes_cli.add_hermes_args(parser)
	args = parser.parse_args()

	hermes_cli.setup_logging(args)
	_LOGGER.debug(args)

	if args.hw_board:
		hw_board = args.hw_board
		_LOGGER.debug("Selected hw is %s", args.hw_board)
	else: 
		_LOGGER.debug("Selected hw is default %s", hw_board)
	if args.led_pattern:
		led_pattern = args.led_pattern
		_LOGGER.debug("Selected led pattern is %s", args.led_pattern)
	else: 
		_LOGGER.debug("Selected led pattern is default %s", led_pattern)

	# Listen for messages
	client = mqtt.Client()
	try:
		hermes = LedManagerHermesMqtt(
			client,
			site_ids=args.site_id,
			hw_led=hw_board,
			pattern=led_pattern,
		)

		_LOGGER.debug("Site %s Connecting to %s:%s", args.site_id, args.host, args.port)
		hermes_cli.connect(client, args)
		client.loop_start()
	except LedManagerHermesMqttException as e:
		_LOGGER.fatal("Fatal Error creating Led Manager -> " + str(e))
		return -1

	try:
		# Run event loop
		asyncio.run(hermes.handle_messages_async())
	except KeyboardInterrupt:
		pass
	finally:
		_LOGGER.debug("Shutting down")
		client.loop_stop()


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
