# imageapp/models.py
from django.db import models

class Image(models.Model):
    title = models.CharField(max_length=255)
    img_width = models.IntegerField()
    img_height = models.IntegerField()
    img_size = models.BigIntegerField()
    img_sha1 = models.CharField(max_length=255)
    img_timestamp = models.DateTimeField()
    img_user_text = models.CharField(max_length=255)
    phash = models.CharField(max_length=64, blank=True, null=True)  # Original pHash

    def __str__(self):
        return self.title


class ScaledImageHash(models.Model):
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name='scaled_hashes')
    width = models.IntegerField()  # Width for the scaled image
    image_width = models.IntegerField()  # Width of the image used to calculate this hash
    hash_algorithm = models.CharField(max_length=10)  # Hash algorithm name (e.g., phash, ahash)
    hash_value = models.CharField(max_length=64)  # Hash value for the image
    is_original = models.BooleanField(default=False)  # Indicates if the image is the original, non-scaled image

    class Meta:
        unique_together = ('image', 'width', 'hash_algorithm', 'is_original')

    def __str__(self):
        original_text = "Original" if self.is_original else f"{self.width}px"
        return f"{self.image.title} - {original_text} - {self.hash_algorithm}"

