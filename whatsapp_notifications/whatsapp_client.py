"""
WhatsApp Cloud API Client
Handles all communication with Meta's WhatsApp Cloud API
"""

import json
import logging
import requests
from typing import Dict, Optional, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """
    Client for Meta WhatsApp Cloud API.
    
    Supports both production (live API) and dry-run (simulation) modes.
    Dry-run mode logs payloads without making actual API calls.
    """

    def __init__(self):
        """Initialize WhatsApp client with configuration from Django settings."""
        self.phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', None)
        self.access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)
        self.api_version = getattr(settings, 'WHATSAPP_API_VERSION', 'v18.0')
        self.dry_run = getattr(settings, 'WHATSAPP_DRY_RUN', True)
        
        # Validate required settings
        if not self.dry_run:
            if not self.phone_number_id or not self.access_token:
                raise ValueError(
                    "WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN "
                    "must be set in Django settings when WHATSAPP_DRY_RUN=False"
                )

    def _build_url(self) -> str:
        """Build the Meta Graph API URL for sending messages."""
        return (
            f"https://graph.facebook.com/{self.api_version}/"
            f"{self.phone_number_id}/messages"
        )

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for API request."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        to: str,
        message_body: str
    ) -> Dict:
        """
        Build the request payload for WhatsApp message.
        
        Args:
            to: Recipient phone number (format: +91XXXXXXXXXX)
            message_body: Message text to send
            
        Returns:
            Dictionary containing the API payload
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_body
            }
        }
        return payload

    def _validate_phone_number(self, phone_number: str) -> Tuple[bool, Optional[str]]:
        """
        Validate phone number format.
        
        Args:
            phone_number: Phone number to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Remove common formatting characters
        cleaned = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # Must start with + and contain only digits after
        if not cleaned.startswith("+"):
            return False, "Phone number must start with '+' (e.g., +91XXXXXXXXXX)"
        
        if not cleaned[1:].isdigit():
            return False, "Phone number must contain only digits after '+'"
        
        if len(cleaned) < 10:
            return False, "Phone number must be at least 10 digits"
        
        return True, None

    def send_text(self, to: str, message_body: str) -> Dict:
        """
        Send a text message via WhatsApp Cloud API.
        
        In dry-run mode, logs the payload without making an API call.
        In production mode, makes actual HTTP POST request to Meta's API.
        
        Args:
            to: Recipient phone number (format: +91XXXXXXXXXX)
            message_body: Text message to send
            
        Returns:
            Dictionary with response status and details
            
        Raises:
            ValueError: If phone number format is invalid
            requests.RequestException: If API request fails (production mode only)
        """
        # Validate phone number
        is_valid, error = self._validate_phone_number(to)
        if not is_valid:
            logger.error(f"Invalid phone number: {error} (received: {to})")
            return {
                "success": False,
                "error": error,
                "mode": "dry_run" if self.dry_run else "production"
            }

        # Validate message body
        if not message_body or len(message_body.strip()) == 0:
            logger.error("Message body cannot be empty")
            return {
                "success": False,
                "error": "Message body cannot be empty",
                "mode": "dry_run" if self.dry_run else "production"
            }

        payload = self._build_payload(to, message_body)

        if self.dry_run:
            # Log payload without making API call
            logger.info(
                f"[DRY RUN] WhatsApp message would be sent\n"
                f"To: {to}\n"
                f"Message: {message_body}\n"
                f"Full Payload: {json.dumps(payload, indent=2)}"
            )
            return {
                "success": True,
                "mode": "dry_run",
                "message": "Message logged (dry-run mode)",
                "payload": payload,
                "to": to
            }
        else:
            # Send actual API request
            try:
                url = self._build_url()
                headers = self._build_headers()

                logger.debug(
                    f"Sending WhatsApp message to {to}\n"
                    f"URL: {url}\n"
                    f"Payload: {json.dumps(payload, indent=2)}"
                )

                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=10
                )

                # Handle API response
                if response.status_code in [200, 201]:
                    response_data = response.json()
                    message_id = response_data.get("messages", [{}])[0].get("id")
                    logger.info(
                        f"WhatsApp message sent successfully to {to} "
                        f"(Message ID: {message_id})"
                    )
                    return {
                        "success": True,
                        "mode": "production",
                        "message_id": message_id,
                        "to": to
                    }
                else:
                    error_msg = response.text
                    logger.error(
                        f"WhatsApp API error (Status {response.status_code}): {error_msg}"
                    )
                    return {
                        "success": False,
                        "mode": "production",
                        "error": f"API returned status {response.status_code}",
                        "details": error_msg,
                        "to": to
                    }

            except requests.Timeout:
                logger.error(f"WhatsApp API request timeout (recipient: {to})")
                return {
                    "success": False,
                    "mode": "production",
                    "error": "API request timeout",
                    "to": to
                }
            except requests.RequestException as e:
                logger.error(f"WhatsApp API request failed: {str(e)}")
                return {
                    "success": False,
                    "mode": "production",
                    "error": f"Request failed: {str(e)}",
                    "to": to
                }
            except Exception as e:
                logger.error(f"Unexpected error sending WhatsApp message: {str(e)}")
                return {
                    "success": False,
                    "mode": "production",
                    "error": f"Unexpected error: {str(e)}",
                    "to": to
                }
