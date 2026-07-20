"""Remote control support for Sony SDCP Projector."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from datetime import timedelta
from functools import partial
from typing import Any

from homeassistant.components.remote import ATTR_NUM_REPEATS, RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pysdcp_extended import Projector

from .commands import (
    POWER_ON,
    POWER_OFF,
    INPUT_HDMI1,
    INPUT_HDMI2,
    ASPECT_RATIO_NORMAL,
    ASPECT_RATIO_V_STRETCH,
    ASPECT_RATIO_ZOOM_1_85,
    ASPECT_RATIO_ZOOM_2_35,
    ASPECT_RATIO_STRETCH,
    ASPECT_RATIO_SQUEEZE,
    PICTURE_POSITION_1_85,
    PICTURE_POSITION_2_35,
    PICTURE_POSITION_CUSTOM_1,
    PICTURE_POSITION_CUSTOM_2,
    PICTURE_POSITION_CUSTOM_3,
)
from .const import ATTR_MANUFACTURER, ATTR_MODEL, DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sony SDCP Projector Remote from a config entry."""

    sdcp = hass.data[DOMAIN][config_entry.entry_id]
    unique_id = config_entry.unique_id

    assert unique_id is not None

    remote = SonySDCPRemote(sdcp, unique_id)

    # Manually update the entity to fetch the initial state
    remote.hass = hass
    await remote.async_update()

    async_add_entities([remote])


class SonySDCPRemote(RemoteEntity):
    """Representation of a Bravia TV Remote."""

    def __init__(
            self,
            sdcp: Projector,
            unique_id: str,
    ) -> None:
        """Initialize Sony SDCP Projector remote."""
        self._sdcp = sdcp
        self._name = f"{ATTR_MANUFACTURER} {ATTR_MODEL}"
        self._state = None
        self._available = False
        self._attr_unique_id = unique_id
        self._attr_current_activity = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer=ATTR_MANUFACTURER,
            model=ATTR_MODEL,
            name=self._name,
        )

    @property
    def available(self):
        """Return if projector is available."""
        return self._available

    @property
    def name(self):
        """Return the display name of this remote."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._state

    async def async_update(self) -> None:
        """Get the latest state from the projector."""
        _LOGGER.debug("Updating the state of '%s'", self.name)

        # Introduce a delay to allow the projector to change state
        await asyncio.sleep(1)

        try:
            self._state = await self.hass.async_add_executor_job(self._sdcp.get_power)
            self._available = True
        except ConnectionRefusedError:
            _LOGGER.error("Projector connection refused")
            self._available = False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the projector on."""
        _LOGGER.debug("Powering on projector '%s'", self.name)

        success = await self.hass.async_add_executor_job(self._sdcp.set_power, True)

        if success:
            _LOGGER.debug("Powered on successfully")
            self._state = True
        else:
            _LOGGER.error("Power on command was not successful")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the projector off."""
        _LOGGER.debug("Powering off projector '%s'", self.name)

        success = await self.hass.async_add_executor_job(self._sdcp.set_power, False)

        if success:
            _LOGGER.debug("Powered off successfully")
            self._state = False
        else:
            _LOGGER.error("Power off command was not successful")

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send a command to device.

        Supported keys: power_on power_off input_hdmi1 input_hdmi2 aspect_ratio_normal
        aspect_ratio_v_stretch aspect_ratio_zoom_1_85 aspect_ratio_zoom_2_35
        aspect_ratio_stretch aspect_ratio_squeeze picture_position_1_85
        picture_position_2_35 picture_position_custom_1 picture_position_custom_2
        picture_position_custom_3
        """
        defined_command_mapping = {
            POWER_ON: self.async_turn_on,
            POWER_OFF: self.async_turn_off,
        }
        command_mapping = {
            INPUT_HDMI1: partial(self._sdcp.set_HDMI_input, 1),
            INPUT_HDMI2: partial(self._sdcp.set_HDMI_input, 2),
            ASPECT_RATIO_NORMAL: partial(
                self._sdcp.set_screen, "ASPECT_RATIO", "NORMAL"
            ),
            ASPECT_RATIO_V_STRETCH: partial(
                self._sdcp.set_screen, "ASPECT_RATIO", "V_STRETCH"
            ),
            ASPECT_RATIO_ZOOM_1_85: partial(
                self._sdcp.set_screen, "ASPECT_RATIO", "ZOOM_1_85"
            ),
            ASPECT_RATIO_ZOOM_2_35: partial(
                self._sdcp.set_screen, "ASPECT_RATIO", "ZOOM_2_35"
            ),
            ASPECT_RATIO_STRETCH: partial(
                self._sdcp.set_screen, "ASPECT_RATIO", "STRETCH"
            ),
            ASPECT_RATIO_SQUEEZE: partial(
                self._sdcp.set_screen, "ASPECT_RATIO", "SQUEEZE"
            ),
            PICTURE_POSITION_1_85: partial(
                self._sdcp.set_screen, "PICTURE_POSITION", "1_85"
            ),
            PICTURE_POSITION_2_35: partial(
                self._sdcp.set_screen, "PICTURE_POSITION", "2_35"
            ),
            PICTURE_POSITION_CUSTOM_1: partial(
                self._sdcp.set_screen, "PICTURE_POSITION", "CUSTOM_1"
            ),
            PICTURE_POSITION_CUSTOM_2: partial(
                self._sdcp.set_screen, "PICTURE_POSITION", "CUSTOM_2"
            ),
            PICTURE_POSITION_CUSTOM_3: partial(
                self._sdcp.set_screen, "PICTURE_POSITION", "CUSTOM_3"
            ),
        }
        repeats = kwargs[ATTR_NUM_REPEATS]

        for _ in range(repeats):
            for single_command in command:
                if single_command in (POWER_ON, POWER_OFF):
                    await defined_command_mapping.get(single_command)(**kwargs)
                else:
                    _LOGGER.debug("Sending command to projector '%s'", single_command)
                    await self.hass.async_add_executor_job(
                        command_mapping.get(single_command)
                    )
