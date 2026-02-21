from .base import DetectorPlugin, CalcDetectat, TipusCalc
from .plugin_llati import DetectorLlati
from .plugin_grec import DetectorGrec
from .plugin_angles import DetectorAngles
from .plugin_rus import DetectorRus
from .plugin_japones import DetectorJapones
from .plugin_arab import DetectorArab
from .plugin_xines import DetectorXines

PLUGINS_DISPONIBLES = {
    "llatí": DetectorLlati,
    "llati": DetectorLlati,
    "la": DetectorLlati,
    "grec": DetectorGrec,
    "grc": DetectorGrec,
    "anglès": DetectorAngles,
    "english": DetectorAngles,
    "en": DetectorAngles,
    "rus": DetectorRus,
    "ru": DetectorRus,
    "japonès": DetectorJapones,
    "ja": DetectorJapones,
    "àrab": DetectorArab,
    "ar": DetectorArab,
    "xinès": DetectorXines,
    "zh": DetectorXines,
}

def obtenir_plugin(llengua: str):
    llengua_norm = llengua.lower()
    clase_plugin = PLUGINS_DISPONIBLES.get(llengua_norm)
    if clase_plugin:
        return clase_plugin()
    return None
