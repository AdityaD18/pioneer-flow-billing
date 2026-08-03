import os
import requests
import logging
from typing import Dict, Any, Optional
from config.settings import settings
from security.token_auth import device_tokens
from cache.offline_queue import enqueue_payload, fetch_and_clear_queue, get_offline_queue_size

logger = logging.getLogger("pioneer_connector.cloud_push")

class CloudPushEngine:
    """
    Outbound-Only Push Sync Engine.
    Initiates outbound HTTPS REST requests from local Connector to Cloud Backend.
    Works behind NAT, CGNAT, and corporate firewalls.
    """

    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        """Constructs security and protocol headers for outbound Cloud REST requests."""
        return {
            "Content-Type": "application/json",
            "User-Agent": "PioneerConnector/2.0.1 (Windows)",
            "Authorization": f"Bearer {device_tokens.get('access_token', '')}",
            "X-Device-ID": device_tokens.get("device_id", ""),
            "X-Pioneer-Version": "2.0.1",
            "X-Protocol-Version": "1.0"
        }

    @classmethod
    def push_to_cloud(cls, payload_type: str, payload_data: Dict[str, Any]) -> bool:
        """
        Pushes a canonical JSON payload to Cloud Backend over HTTPS.
        If network fails, enqueues to local SQLite queue for auto-drain when online.
        """
        cloud_url = getattr(settings, "CLOUD_BACKEND_URL", None) or os.environ.get("CLOUD_BACKEND_URL")
        
        # If no Cloud URL configured (local standalone mode), complete cleanly
        if not cloud_url:
            logger.info("No CLOUD_BACKEND_URL set; operating in local mode.")
            return True

        endpoint = f"{cloud_url.rstrip('/')}/api/v1/sync/push"
        try:
            # Drain any previously queued offline items first
            cls.flush_offline_queue()

            resp = requests.post(
                url=endpoint,
                json={
                    "payload_type": payload_type,
                    "device_id": device_tokens.get("device_id"),
                    "data": payload_data
                },
                headers=cls.get_headers(),
                timeout=10.0
            )

            if resp.status_code in (200, 201):
                logger.info(f"[CloudPush] Successfully pushed {payload_type} to Cloud Backend.")
                return True
            else:
                logger.warning(f"[CloudPush] Cloud Backend returned HTTP {resp.status_code}. Queueing payload.")
                enqueue_payload(payload_type, payload_data)
                return False
        except Exception as e:
            logger.warning(f"[CloudPush] Network unreachable ({e}). Enqueuing {payload_type} to offline SQLite queue.")
            enqueue_payload(payload_type, payload_data)
            return False

    @classmethod
    def flush_offline_queue(cls):
        """Flushes enqueued offline payloads to Cloud Backend when connectivity is active."""
        cloud_url = getattr(settings, "CLOUD_BACKEND_URL", None) or os.environ.get("CLOUD_BACKEND_URL")
        if not cloud_url or get_offline_queue_size() == 0:
            return

        queued_items = fetch_and_clear_queue()
        logger.info(f"[CloudPush] Draining {len(queued_items)} queued offline payloads to Cloud.")
        
        endpoint = f"{cloud_url.rstrip('/')}/api/v1/sync/push"
        for item in queued_items:
            try:
                requests.post(
                    url=endpoint,
                    json={
                        "payload_type": item["payload_type"],
                        "device_id": device_tokens.get("device_id"),
                        "data": item["payload_data"]
                    },
                    headers=cls.get_headers(),
                    timeout=8.0
                )
            except Exception as e:
                logger.warning(f"[CloudPush] Failed to flush queued payload item {item['id']}: {e}")
                # Re-enqueue remaining
                enqueue_payload(item["payload_type"], item["payload_data"])
                break
