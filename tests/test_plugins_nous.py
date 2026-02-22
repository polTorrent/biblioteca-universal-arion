import pytest
from utils.calcs_plugins.plugin_frances import DetectorFrances
from utils.calcs_plugins.plugin_alemany import DetectorAlemany

def test_detector_frances():
    detector = DetectorFrances()
    assert detector.llengua == "francès"
    
    text_amb_errors = "Ell solia entendre les propostes de mala gana i attendre sense protestar."
    resultats = detector.detectar(text_amb_errors)
    
    termes_detectats = [r.text_original.lower() for r in resultats]
    assert "entendre" in termes_detectats
    assert "attendre" in termes_detectats
    assert len(resultats) >= 2

def test_detector_alemany():
    detector = DetectorAlemany()
    assert detector.llengua == "alemany"
    
    text_amb_errors = "El jove va conseguir bekommen el seu títol al gymnasium de la ciutat."
    resultats = detector.detectar(text_amb_errors)
    
    termes_detectats = [r.text_original.lower() for r in resultats]
    assert "bekommen" in termes_detectats
    assert "gymnasium" in termes_detectats
    assert len(resultats) >= 2
    
def test_absencia_errors():
    det_fr = DetectorFrances()
    det_de = DetectorAlemany()
    text_net = "Escoltar i esperar són virtuts, com comprendre l'institut."
    assert len(det_fr.detectar(text_net)) == 0
    assert len(det_de.detectar(text_net)) == 0
