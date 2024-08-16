# imageapp/management/commands/fetch_images.py
import requests
from django.core.management.base import BaseCommand
from benchmark.models import Image
from datetime import datetime

class Command(BaseCommand):
    help = 'Fetches image data from the specified URL and stores it in the database.'

    def handle(self, *args, **kwargs):
        url = 'https://petscan.wmcloud.org/?psid=29099516&format=json&output_limit=50'
        response = requests.get(url)
        data = response.json()

        images = data.get('*', [])[0].get('a', {}).get('*', [])

        for image_data in images:
            metadata = image_data.get('metadata', {})
            img_timestamp = datetime.strptime(metadata['img_timestamp'], '%Y%m%d%H%M%S')

            Image.objects.create(
                title=image_data['title'],
                img_width=metadata['img_width'],
                img_height=metadata['img_height'],
                img_size=metadata['img_size'],
                img_sha1=metadata['img_sha1'],
                img_timestamp=img_timestamp,
                img_user_text=metadata['img_user_text'],
            )

        self.stdout.write(self.style.SUCCESS('Successfully fetched and stored image data'))
