# imageapp/management/commands/fetch_image_urls.py
import pywikibot
import requests
import hashlib
import os
from PIL import Image as PILImage
import imagehash
from imagehash import ImageHash
from io import BytesIO
from django.core.management.base import BaseCommand
from django.conf import settings
from benchmark.models import Image, ScaledImageHash
import numpy

def phash_custom(image, hash_size=8, highfreq_factor=4, resize_first=False, resample_mode=imagehash.ANTIALIAS):
    # type: (Image.Image, int, int) -> ImageHash
    """
    Perceptual Hash computation.

    Implementation follows https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html

    @image must be a PIL instance.
    """
    if hash_size < 2:
        raise ValueError('Hash size must be greater than or equal to 2')

    import scipy.fftpack
    img_size = hash_size * highfreq_factor
    if resize_first:
        image = image.resize((img_size, img_size), imagehash.ANTIALIAS).convert('L')
    else:
        image = image.convert('L').resize((img_size, img_size), imagehash.ANTIALIAS)

    pixels = numpy.asarray(image)
    dct = scipy.fftpack.dct(scipy.fftpack.dct(pixels, axis=0), axis=1)
    dctlowfreq = dct[:hash_size, :hash_size]
    med = numpy.median(dctlowfreq)
    diff = dctlowfreq > med
    return ImageHash(diff)

def phash_resize_first(image):
    return phash_custom(image, resize_first=True)

class Command(BaseCommand):
    help = 'Fetches the URL of image files using Pywikibot FilePage, calculates various hashes, stores images, and stores hashes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hash_algorithms',
            nargs='+',
            type=str,
            default=['phash'],
            help='Specify hash algorithms to use (options: phash, phash_simple, phash_resize_first, ahash, dhash, whash). Default is phash.'
        )

    def handle(self, *args, **options):
        # Set up the Pywikibot site for Wikimedia Commons
        site = pywikibot.Site('commons', 'commons')

        # Use the custom user-agent from settings
        headers = {
            'User-Agent': settings.CUSTOM_USER_AGENT
        }

        # Directory to store images
        image_dir = os.path.join(settings.BASE_DIR, 'stored_images')
        os.makedirs(image_dir, exist_ok=True)

        # List of widths to request
        widths = [256, 640, 800, 1024, 2048]

        # Get the hash algorithms to use
        hash_algorithms = options['hash_algorithms']
        available_hashes = {
            'phash': imagehash.phash,
            'phash_simple': imagehash.phash_simple,
            'phash_resize_first': phash_resize_first,
            'ahash': imagehash.average_hash,
            'dhash': imagehash.dhash,
            'whash': imagehash.whash
        }

        # Filter images directly in the database query
        images = Image.objects.filter(img_width__gt=1500, img_height__gt=1500)

        for image in images:
            try:
                self.stdout.write(self.style.SUCCESS(f"Processing image {image.title} with size {image.img_width}x{image.img_height}"))

                # Create a Pywikibot FilePage for the file
                file_page = pywikibot.FilePage(site, f"File:{image.title}")

                # Get the original image URL using get_file_url()
                if file_page.exists():
                    image_url = file_page.get_file_url()
                    self.stdout.write(self.style.SUCCESS(f"Original Image URL for {image.title}: {image_url}"))

                    # Generate the MD5 hash of the image URL
                    image_filename = f"{hashlib.md5(image_url.encode('utf-8')).hexdigest()}.jpg"
                    image_path = os.path.join(image_dir, image_filename)

                    # Check if the file already exists locally
                    if os.path.exists(image_path):
                        self.stdout.write(self.style.SUCCESS(f"Using cached file: {image_filename}"))
                    else:
                        # Fetch the image and store it on the filesystem
                        response = requests.get(image_url, headers=headers)
                        with open(image_path, 'wb') as file:
                            file.write(response.content)
                        self.stdout.write(self.style.SUCCESS(f"Image saved as {image_filename}"))

                    # Open the image with Pillow
                    img = PILImage.open(image_path)

                    # Calculate and store the specified hashes for the original image
                    for algorithm in hash_algorithms:
                        if algorithm in available_hashes:
                            hash_func = available_hashes[algorithm]
                            original_hash = hash_func(img)
                            self.stdout.write(self.style.SUCCESS(f"{algorithm} for {image.title}: {original_hash}"))

                            # Store the hash in the database
                            ScaledImageHash.objects.update_or_create(
                                image=image,
                                width=image.img_width,  # Use original width for the original image
                                image_width=image.img_width,
                                hash_algorithm=algorithm,
                                is_original=True,
                                defaults={'hash_value': str(original_hash)}
                            )

                    # Process the scaled image sizes
                    for width in widths:
                        scaled_url = file_page.get_file_url(url_width=width)
                        scaled_filename = f"{hashlib.md5(scaled_url.encode('utf-8')).hexdigest()}.jpg"
                        scaled_image_path = os.path.join(image_dir, scaled_filename)

                        # Check if the scaled file already exists locally
                        if os.path.exists(scaled_image_path):
                            self.stdout.write(self.style.SUCCESS(f"Using cached scaled file: {scaled_filename}"))
                        else:
                            # Fetch the scaled image and store it on the filesystem
                            response = requests.get(scaled_url, headers=headers)
                            with open(scaled_image_path, 'wb') as file:
                                file.write(response.content)
                            self.stdout.write(self.style.SUCCESS(f"Scaled image saved as {scaled_filename}"))

                        # Open the scaled image with Pillow
                        scaled_img = PILImage.open(scaled_image_path)

                        # Calculate and store the specified hashes for the scaled image
                        for algorithm in hash_algorithms:
                            if algorithm in available_hashes:
                                hash_func = available_hashes[algorithm]
                                scaled_hash = hash_func(scaled_img)
                                self.stdout.write(self.style.SUCCESS(f"{algorithm} for {image.title} ({width}px): {scaled_hash}"))

                                # Store the scaled image hash in the database
                                ScaledImageHash.objects.update_or_create(
                                    image=image,
                                    width=width,
                                    image_width=width,
                                    hash_algorithm=algorithm,
                                    is_original=False,
                                    defaults={'hash_value': str(scaled_hash)}
                                )
                else:
                    self.stdout.write(self.style.WARNING(f"File not found for {image.title}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {image.title}: {str(e)}"))

