#! /usr/bin/env python3
"""Monitor disk usage and send to Home Assistant.

Inspired by:
https://community.home-assistant.io/t/how-to-disk-space-sensor/686376.
"""

import argparse
import logging
import os
import pathlib
import shutil
import socket
import time

import dotenv
import requests


def main(hostname: str, path: pathlib.Path, mount: str,
         ha_rest_api_url: str, interval: float):
    """Periodically reports disk usage to Home Assistant.

    Sensor will be called `sensor.HOSTNAME_MOUNT_disk_usage`.
    """
    key = os.getenv("HA_API_KEY")
    assert key, "Need to specify HA_API_KEY in environment!"
    assert ha_rest_api_url, "Please specify HA_REST_API_URL"
    assert interval > 0, "Stubbornly refusing to run tight loop"

    while True:
        usage = shutil.disk_usage(path)
        used_percentage = (usage.used * 100) / usage.total
        free_percentage = (usage.free * 100) / usage.total

        headers = {"Authorization": f"Bearer {key}"}
        json = {
            "state": used_percentage,
            "attributes": {
                "friendly_name": f"{hostname} {mount} Disk Usage",
                "unit_of_measurement": "%",
                "used_percentage": used_percentage,
                "free_percentage": free_percentage,
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
            },
        }

        url = os.path.join(
            ha_rest_api_url,
            "states",
            f"sensor.{hostname}_{mount}_disk_usage")
        logging.debug("Posting to %r: json %r", url, json)
        try:
            response = requests.post(url,
                                     headers=headers,
                                     json=json)
            logging.debug("Got response %r", response)
            if response.json():
                logging.debug("Response JSON: %r", response.json())
        except Exception as e:
            logging.error("Got exception: %r, %s", e, e)
        logging.debug("Sleeping %fs", interval)
        time.sleep(interval)


if __name__ == "__main__":
    dotenv.load_dotenv()
    parser = argparse.ArgumentParser(
        description="Monitor disk usage in Home Assistant",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("path", type=pathlib.Path,
                        help="Path to monitor")
    parser.add_argument("mount",
                        help="Name of the mount (used in sensor name)")
    parser.add_argument("--hostname",
                        help="Hostname (used in sensor name)",
                        default=socket.gethostname())
    parser.add_argument("--interval", type=float,
                        help="Reporting interval, in seconds",
                        default=60.0)
    parser.add_argument("--ha-rest-api-url",
                        help=("Home Assistant REST API URL " +
                              "(or specify in HA_REST_API_URL)"),
                        default=os.getenv("HA_REST_API_URL"))
    parser.add_argument("--log-level",
                        help="Logging level (default INFO)",
                        default=logging.INFO,
                        type=logging.getLevelName)
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    main(args.hostname,
         args.path,
         args.mount,
         args.ha_rest_api_url,
         args.interval)
