"""
mqtt_publisher.py — Publication MQTT des événements GuardianAI Gateway

Publie sur les topics :
  guardian/devices     → nouvel appareil détecté
  guardian/dns         → requête DNS catégorisée
  guardian/rules       → règle appliquée/retirée
  guardian/alerts      → alertes (usage anormal, blocage)

Le broker Mosquitto tourne dans Docker (port 1883).
Grafana ou tout autre client MQTT peut s'y abonner.
"""

import json
import logging
from datetime import datetime

log = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
    _MQTT_AVAILABLE = True
except ImportError:
    _MQTT_AVAILABLE = False

BROKER_HOST = "localhost"
BROKER_PORT = 1883
BASE_TOPIC = "guardian"

_client = None


def _get_client():
    """Retourne un client MQTT connecté (singleton)."""
    global _client
    if not _MQTT_AVAILABLE:
        return None
    if _client is None or not _client.is_connected():
        try:
            _client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            _client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            _client.loop_start()
            log.info("MQTT connecté à %s:%d", BROKER_HOST, BROKER_PORT)
        except Exception as e:
            log.warning("MQTT indisponible : %s", e)
            _client = None
    return _client


def publish(topic: str, payload: dict):
    """Publie un message JSON sur un topic MQTT."""
    client = _get_client()
    if client is None:
        return

    payload["timestamp"] = datetime.now().isoformat()
    message = json.dumps(payload, ensure_ascii=False, default=str)

    client.publish(f"{BASE_TOPIC}/{topic}", message)
    log.debug("MQTT -> %s/%s : %s", BASE_TOPIC, topic, message)


def publish_device(mac, ip, hostname, vendor, device_type, confidence):
    """Publie la détection d'un appareil."""
    publish("devices", {
        "mac": mac,
        "ip": ip,
        "hostname": hostname,
        "vendor": vendor,
        "device_type": device_type,
        "confidence": confidence,
    })


def publish_dns(ip, domain, category):
    """Publie une requête DNS catégorisée."""
    publish("dns", {
        "ip": ip,
        "domain": domain,
        "category": category,
    })


def publish_rule(rule_id, action, mac, rule_type, target=None):
    """Publie une action de règle (appliquée/retirée)."""
    publish("rules", {
        "rule_id": rule_id,
        "action": action,
        "mac": mac,
        "rule_type": rule_type,
        "target": target,
    })


def publish_alert(alert_type, message, mac=None):
    """Publie une alerte (usage anormal, etc.)."""
    publish("alerts", {
        "alert_type": alert_type,
        "message": message,
        "mac": mac,
    })


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print(f"MQTT disponible : {_MQTT_AVAILABLE}")
    publish_device("f0:67:28:90:81:1d", "192.168.50.52",
                   "OPPO-A31", "OPPO", "Smartphone", 0.9)
    publish_dns("192.168.50.52", "tiktok.com", "reseaux_sociaux")
    publish_alert("test", "Ceci est un test d'alerte")
    print("Messages publiés. Ctrl+C pour quitter.")
