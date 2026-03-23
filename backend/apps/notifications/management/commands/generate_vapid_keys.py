"""
Generate VAPID key pair for Web Push notifications.
Outputs the two lines to add to your .env file.

Usage:
    python manage.py generate_vapid_keys
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Generate VAPID key pair for Web Push notifications.'

    def handle(self, *args, **options):
        try:
            import base64
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives.serialization import (
                Encoding, NoEncryption, PrivateFormat, PublicFormat,
            )
        except ImportError:
            self.stderr.write('cryptography package not installed. Run: pip install cryptography')
            return

        key = ec.generate_private_key(ec.SECP256R1())

        priv_der = key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
        priv_b64 = base64.urlsafe_b64encode(priv_der).rstrip(b'=').decode()

        pub_bytes = key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b'=').decode()

        self.stdout.write('\nAdd these to your .env file:\n')
        self.stdout.write(self.style.SUCCESS(f'VAPID_PRIVATE_KEY={priv_b64}'))
        self.stdout.write(self.style.SUCCESS(f'VAPID_PUBLIC_KEY={pub_b64}'))
        self.stdout.write('\nAdd this to your frontend .env:\n')
        self.stdout.write(self.style.SUCCESS(f'VITE_VAPID_PUBLIC_KEY={pub_b64}'))
        self.stdout.write('')
