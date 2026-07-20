import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pysdcp_extended import Projector, ACTIONS, COMMANDS

from .const import ATTR_MODEL, ATTR_MANUFACTURER, DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sony SDCP Projector Remote from a config entry."""

    sdcp = hass.data[DOMAIN][config_entry.entry_id]
    assert config_entry.unique_id is not None

    unique_id = f"{config_entry.unique_id}_status"

    status = SonySDCPStatus(sdcp, unique_id)

    # Manually update the entity to fetch the initial state
    status.hass = hass
    await status.async_update()

    async_add_entities([status])

class SonySDCPStatus(SensorEntity):
    def __init__(
            self,
            sdcp: Projector,
            unique_id: str,
    ) -> None:
        self._sdcp = sdcp
        self._name = f"{ATTR_MANUFACTURER} {ATTR_MODEL} Status"
        self._attr_native_value = None
        self._attr_state_class = None
        self._attr_unique_id = unique_id
        self._attr_device_class = None
        self._available = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer=ATTR_MANUFACTURER,
            model=ATTR_MODEL,
            name=self._name,
        )

    # noinspection protected-member
    async def async_update(self) -> None:
        _LOGGER.debug("Updating the state of '%s'", self.name)

        # noinspection protected-member
        try:
            self._attr_native_value = await (self.hass.async_add_executor_job(lambda:
                                                                              self._sdcp._send_command(
                                                                                  action=ACTIONS["GET"],
                                                                                  command=COMMANDS[
                                                                                      "GET_STATUS_POWER"],
                                                                              )
                                                                              )
                                             )
            self._available = True
        except ConnectionRefusedError:
            _LOGGER.error("Projector connection refused")
            self._available = False
