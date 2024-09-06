# imageapp/management/commands/analyze_hashes.py
from django.core.management.base import BaseCommand
from benchmark.models import Image, ScaledImageHash
from imagehash import hex_to_hash

class Command(BaseCommand):
    help = 'Analyzes how well scaled hashes match the original image hashes and checks for hash collisions between different images.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hash-algorithms',
            nargs='+',
            type=str,
            default=['phash'],
            help='Specify hash algorithms to analyze (options: phash, phash_simple, phash_resize_first, ahash, dhash, whash). Default is phash.'
        )

    def handle(self, *args, **options):
        hash_algorithms = options['hash_algorithms']  # Get the hash algorithms to analyze
        direct_matches = {algorithm: 0 for algorithm in hash_algorithms}
        hash_collisions = {algorithm: 0 for algorithm in hash_algorithms}
        scaled_collisions = {algorithm: 0 for algorithm in hash_algorithms}
        original_hashes_processed = {algorithm: 0 for algorithm in hash_algorithms}
        scaled_hashes_processed = {algorithm: 0 for algorithm in hash_algorithms}
        original_images_processed = 0  # Counter for original images processed

        # Analyze each image
        for image in Image.objects.all():
            original_image_processed = False  # Track if we process any original hashes for this image
            for algorithm in hash_algorithms:
                original_hash_record = ScaledImageHash.objects.filter(image=image, is_original=True, hash_algorithm=algorithm).first()

                if original_hash_record:
                    original_image_processed = True
                    original_hash = hex_to_hash(original_hash_record.hash_value)
                    original_hashes_processed[algorithm] += 1  # Increment original hashes processed
                    self.stdout.write(self.style.SUCCESS(f"Analyzing {algorithm} for image: {image.title}"))

                    # Compare scaled hashes with the original hash
                    scaled_hashes = ScaledImageHash.objects.filter(image=image, is_original=False, hash_algorithm=algorithm)
                    for scaled_hash_record in scaled_hashes:
                        scaled_hash = hex_to_hash(scaled_hash_record.hash_value)
                        scaled_hashes_processed[algorithm] += 1  # Increment scaled hashes processed
                        distance = original_hash - scaled_hash  # Hamming distance

                        if distance == 0:
                            direct_matches[algorithm] += 1

                        self.stdout.write(f"  - Scaled {scaled_hash_record.width}px: Hamming distance = {distance}")

                    # Check for hash collisions with other images for the scaled hashes
                    scaled_collisions_found = self.check_scaled_hash_collisions(image, scaled_hashes, algorithm)
                    scaled_collisions[algorithm] += scaled_collisions_found

                    # Check for hash collisions with other original images
                    collisions_found = self.check_for_collisions(image, original_hash, algorithm)
                    hash_collisions[algorithm] += collisions_found
                else:
                    self.stdout.write(self.style.WARNING(f"No {algorithm} hash found for image: {image.title}"))

            # If any original hash was processed for this image, increment the counter
            if original_image_processed:
                original_images_processed += 1

        # Print the summary
        self.print_summary(direct_matches, hash_collisions, scaled_collisions, original_hashes_processed, scaled_hashes_processed, original_images_processed)

    def check_for_collisions(self, current_image, original_hash, algorithm):
        """Check if any other images have the same original hash as the current image."""
        collisions = 0
        
        other_images = Image.objects.exclude(id=current_image.id).exclude(scaled_hashes__isnull=True)
            
        # Check collisions with original images
        for other_image in other_images:
            other_hash_record = ScaledImageHash.objects.filter(image=other_image, is_original=True, hash_algorithm=algorithm).first()
            if other_hash_record:
                other_hash = hex_to_hash(other_hash_record.hash_value)
                if original_hash == other_hash:
                    self.stdout.write(self.style.ERROR(
                        f"Hash collision detected for {algorithm} between {current_image.title} and {other_image.title}"
                    ))
                    collisions += 1

        return collisions

    def check_scaled_hash_collisions(self, original_image, scaled_hashes, algorithm):
        """Check for hash collisions between scaled images and other images' scaled hashes."""
        collisions = 0
        for scaled_hash_record in scaled_hashes:
            # Query for any other image with the same hash, excluding images derived from the original image
            collision_candidates = ScaledImageHash.objects.filter(
                hash_value=scaled_hash_record.hash_value,
                hash_algorithm=algorithm,
                is_original=False
            ).exclude(image__id=original_image.id)

            for candidate in collision_candidates:
                self.stdout.write(self.style.ERROR(
                    f"Scaled hash collision detected for {algorithm} between scaled image of {original_image.title} "
                    f"and {candidate.image.title} (width {scaled_hash_record.width}px)"
                ))
                collisions += 1

        return collisions

    def print_summary(self, direct_matches, hash_collisions, scaled_collisions, original_hashes_processed, scaled_hashes_processed, original_images_processed):
        """Print a summary of the analysis results."""
        self.stdout.write(self.style.SUCCESS("\nSummary:"))
        self.stdout.write(f"Original images processed: {original_images_processed}")
        for algorithm in direct_matches.keys():
            self.stdout.write(self.style.SUCCESS(f"Algorithm: {algorithm}"))
            self.stdout.write(f"  Original image hashes processed: {original_hashes_processed[algorithm]}")
            self.stdout.write(f"  Scaled image hashes processed: {scaled_hashes_processed[algorithm]}")
            self.stdout.write(f"  Direct matches: {direct_matches[algorithm]}")
            self.stdout.write(f"  Hash collisions (original vs. original): {hash_collisions[algorithm]}")
            self.stdout.write(f"  Hash collisions (scaled vs. scaled): {scaled_collisions[algorithm]}")

    def check_for_collisions2(self, current_image, original_hash, algorithm):
        """Check for hash collisions for both original and scaled images."""
        collisions = 0
        scaled_collisions = 0
            
            
        other_images = Image.objects.exclude(id=current_image.id).exclude(scaled_hashes__isnull=True)
            
        # Check collisions with original images
        for other_image in other_images:
            other_hash_record = ScaledImageHash.objects.filter(image=other_image, is_original=True, hash_algorithm=algorithm).first()
            if other_hash_record:
                other_hash = hex_to_hash(other_hash_record.hash_value)
                if original_hash == other_hash:
                    self.stdout.write(self.style.ERROR(
                        f"Hash collision detected for {algorithm} between {current_image.title} and {other_image.title}"
                    ))
                    collisions += 1
        
        # Check collisions between scaled images
        scaled_hashes = ScaledImageHash.objects.filter(is_original=False, hash_algorithm=algorithm, image=current_image)
        for hash_record in scaled_hashes:
            test_hashes = ScaledImageHash.objects.filter(is_original=False, hash_algorithm=algorithm, hash_value=hash_record.hash_value).exclude(image=current_image)
            for test_hash in test_hashes:
                self.stdout.write(self.style.ERROR(
                    f"Scaled hash collision detected for {algorithm} between scaled images of {current_image.title} and {test_hash.image.title}"
                ))
                scaled_collisions += 1

        return collisions, scaled_collisions

