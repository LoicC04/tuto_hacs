""" Implements the Tuto HACS sensors component """
import logging
from datetime import datetime, timedelta
import voluptuous as vol

from homeassistant.const import UnitOfTime, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback, Event, State
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)

from homeassistant.helpers.event import (
    async_track_time_interval,
    async_track_state_change_event,
)

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.device_registry import DeviceEntryType

import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    CONF_NAME,
    SERVICE_RAZ_COMPTEUR,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Configuration des entités sensor à partir de la configuration
    ConfigEntry passée en argument"""

    _LOGGER.debug("Calling async_setup_entry entry=%s", entry)

    entity1 = TutoHacsElapsedSecondEntity(hass, entry)
    entity2 = TutoHacsListenEntity(hass, entry, entity1)
    async_add_entities([entity1, entity2], True)

    # Add services
    platform = async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_RAZ_COMPTEUR,
        {vol.Optional("valeur_depart"): cv.positive_int},
        "service_raz_compteur",
    )


class TutoHacsElapsedSecondEntity(SensorEntity):
    """La classe de l'entité TutoHacs"""

    _hass: HomeAssistant

    def __init__(
        self,
        hass: HomeAssistant,  # pylint: disable=unused-argument
        config_entry: ConfigEntry,
    ) -> None:
        """Initisalisation de notre entité"""
        self._hass = hass
        self._attr_has_entity_name = True
        self._attr_name = config_entry.data.get(CONF_NAME)
        self._device_id = config_entry.entry_id
        self._attr_unique_id = self._attr_name + "_seconds"
        self._attr_native_value = 12

    @property
    def should_poll(self) -> bool:
        """Do not poll for those entities"""
        return False

    @property
    def icon(self) -> str | None:
        return "mdi:timer-play"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.DURATION

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfTime.SECONDS

    @property
    def device_info(self) -> DeviceInfo:
        """Donne le lien avec le device. Non utilisé jusqu'au tuto 4"""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_id,
            manufacturer=DEVICE_MANUFACTURER,
            model=DOMAIN,
        )

    @callback
    async def async_added_to_hass(self):
        """Ce callback est appelé lorsque l'entité est ajoutée à HA"""

        # Arme le timer
        timer_cancel = async_track_time_interval(
            self._hass,
            self._incremente_secondes,  # La methode à appeler périodiquement
            interval=timedelta(seconds=1),
        )
        # desarme le timer lors de la destruction de l'entité
        self.async_on_remove(timer_cancel)

    @callback
    async def _incremente_secondes(self, _):
        """Cette méthode va être appelée toutes les secondes"""
        _LOGGER.info("Appel de incremente_secondes à %s", datetime.now())

        # On incrémente la valeur de notre etat
        self._attr_native_value += 1

        # On sauvegarde le nouvel état
        self.async_write_ha_state()

        # Toutes les 5 secondes on envoie un event
        if self._attr_native_value % 5 == 0:
            self._hass.bus.fire(
                "event_changement_etat_TutoHacsElapsedSecondEnity",
                {"nb_secondes": self._attr_native_value},
            )

    async def service_raz_compteur(self, valeur_depart: int):
        """Appelée lors de l'invocation du service 'raz_compteur'
        Elle prend en argument la 'valeur_depart' qui est
        construite à partir du paramètre 'valeur_depart'
        """
        _LOGGER.info(
            "Appel du service service_raz_compteur valeur_depart: %d", valeur_depart
        )
        self._attr_native_value = valeur_depart if valeur_depart is not None else 0

        # On sauvegarde le nouvel état
        self.async_write_ha_state()


class TutoHacsListenEntity(SensorEntity):
    """La classe de l'entité TutoHacs qui écoute la première"""

    _hass: HomeAssistant
    _entity_to_listen: TutoHacsElapsedSecondEntity

    def __init__(
        self,
        hass: HomeAssistant,  # pylint: disable=unused-argument
        config_entry: ConfigEntry,
        entity_to_listen: TutoHacsElapsedSecondEntity,  # L'entité qu'on veut écouter
    ) -> None:
        """Initisalisation de notre entité"""
        self._hass = hass
        self._attr_has_entity_name = True
        # On lui donne un nom et un unique_id différent
        self._device_id = config_entry.entry_id
        self._attr_name = config_entry.data.get(CONF_NAME) + " Ecouteur"
        self._attr_unique_id = self._attr_name + "_ecouteur"
        # Pas de valeur tant qu'on n'a pas reçu
        self._attr_native_value = None
        self._entity_to_listen = entity_to_listen

    @property
    def should_poll(self) -> bool:
        """Pas de polling pour mettre à jour l'état"""
        return False

    @property
    def icon(self) -> str | None:
        return "mdi:timer-settings-outline"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        """Cette entité"""
        return SensorDeviceClass.TIMESTAMP

    @property
    def device_info(self) -> DeviceInfo:
        """Donne le lien avec le device. Non utilisé jusqu'au tuto 4"""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_id,
            manufacturer=DEVICE_MANUFACTURER,
            model=DOMAIN,
        )

    @callback
    async def async_added_to_hass(self):
        """Ce callback est appelé lorsque l'entité est ajoutée à HA"""

        # Arme l'écoute de la première entité
        listener_cancel = async_track_state_change_event(
            self.hass,
            [self._entity_to_listen.entity_id],
            self._on_event,
        )
        # desarme le timer lors de la destruction de l'entité
        self.async_on_remove(listener_cancel)

    @callback
    async def _on_event(self, event: Event):
        """Cette méthode va être appelée à chaque fois que l'entité
        "entity_to_listen" publie un changement d'état"""

        _LOGGER.info("Appel de _on_event à %s avec l'event %s",
                     datetime.now(), event)

        new_state: State = event.data.get("new_state")
        # old_state: State = event.data.get("old_state")

        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.warning("Pas d'état disponible. Evenement ignoré")
            return

        # state.last_changed.astimezone(self._current_tz)

        # On recherche la date de l'event pour la stocker dans notre état
        self._attr_native_value = new_state.last_changed

        # On sauvegarde le nouvel état
        self.async_write_ha_state()
