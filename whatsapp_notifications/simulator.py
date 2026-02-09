"""
WhatsApp Mock Message Receiver
Simulates receiving WhatsApp messages for testing purposes.
Useful for testing message handling without real WhatsApp integration.
"""

import json
import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)


class WhatsAppMessageSimulator:
    """
    Simulates WhatsApp Cloud API incoming messages.
    Used for testing webhook handlers and message processing.
    """

    @staticmethod
    def create_incoming_message(
        from_phone: str,
        message_body: str,
        message_id: str = None,
        timestamp: str = None
    ) -> Dict:
        """
        Create a mock incoming WhatsApp message in Meta API format.
        
        Args:
            from_phone: Sender phone number (e.g., "+919876543210")
            message_body: Message text
            message_id: Message ID (auto-generated if not provided)
            timestamp: Message timestamp (current time if not provided)
            
        Returns:
            Dictionary containing webhook payload in Meta API format
        """
        if message_id is None:
            import uuid
            message_id = f"wamid.{str(uuid.uuid4())[:20]}"
        
        if timestamp is None:
            timestamp = str(int(datetime.now().timestamp()))
        
        # Format: Remove + and any spaces
        phone_cleaned = from_phone.replace("+", "").replace(" ", "")
        
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "1234567890",
                                    "phone_number_id": "1234567890123456"
                                },
                                "contacts": [
                                    {
                                        "profile": {
                                            "name": "Test User"
                                        },
                                        "wa_id": phone_cleaned
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": phone_cleaned,
                                        "id": message_id,
                                        "timestamp": timestamp,
                                        "type": "text",
                                        "text": {
                                            "body": message_body
                                        }
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ],
                    "timestamp": timestamp
                }
            ]
        }
        
        return payload

    @staticmethod
    def simulate_order_confirmation_received(
        customer_phone: str,
        order_id: int
    ) -> Dict:
        """
        Simulate receiving an order confirmation message.
        
        Args:
            customer_phone: Customer's WhatsApp phone number
            order_id: Order ID
            
        Returns:
            Mock incoming message payload
        """
        message_body = (
            f"🎉 Your order #{order_id} is confirmed!\n\n"
            f"Items: Product A x2, Product B x1\n"
            f"Total: ₹5000.00\n\n"
            f"We will update you on the delivery status soon.\n"
            f"Thank you for shopping with The Mannan Crackers!"
        )
        
        return WhatsAppMessageSimulator.create_incoming_message(
            from_phone=customer_phone,
            message_body=message_body
        )

    @staticmethod
    def print_mock_message(payload: Dict):
        """
        Pretty-print a mock WhatsApp message.
        
        Args:
            payload: Webhook payload dictionary
        """
        print("\n" + "="*70)
        print("📱 SIMULATED WHATSAPP MESSAGE RECEIVED")
        print("="*70)
        
        try:
            message_data = payload['entry'][0]['changes'][0]['value']['messages'][0]
            contact_data = payload['entry'][0]['changes'][0]['value']['contacts'][0]
            
            phone = message_data['from']
            message_id = message_data['id']
            timestamp = message_data['timestamp']
            message_body = message_data['text']['body']
            sender_name = contact_data['profile']['name']
            
            print(f"From: {sender_name}")
            print(f"Phone: +{phone}")
            print(f"Message ID: {message_id}")
            print(f"Timestamp: {timestamp}")
            print("-" * 70)
            print(f"Message:\n{message_body}")
            print("=" * 70 + "\n")
            
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing message: {str(e)}")
            print(f"Error: Could not parse message")

    @staticmethod
    def print_raw_json(payload: Dict):
        """
        Print the raw JSON payload.
        
        Args:
            payload: Webhook payload dictionary
        """
        print("\n" + "="*70)
        print("📋 RAW WEBHOOK PAYLOAD (JSON)")
        print("="*70)
        print(json.dumps(payload, indent=2))
        print("=" * 70 + "\n")


def test_dry_run_message_simulation():
    """
    Test the message simulator with a sample order notification.
    """
    print("\n🔧 WhatsApp Message Simulator - Test Mode\n")
    
    # Create a simulated incoming message
    payload = WhatsAppMessageSimulator.simulate_order_confirmation_received(
        customer_phone="+918074101457",
        order_id=123
    )
    
    # Print formatted message
    WhatsAppMessageSimulator.print_mock_message(payload)
    
    # Print raw JSON
    WhatsAppMessageSimulator.print_raw_json(payload)
    
    logger.info("Test message simulation completed successfully")


if __name__ == "__main__":
    test_dry_run_message_simulation()
