from django.db import models

# Create your models here.

class TarotCard(models.Model):
    name = models.CharField(max_length=100)
    image = models.CharField(max_length=200)  # Or ImageField if you use media
    meaning = models.TextField()
    position = models.CharField(max_length=100, blank=True, null=True)
    position_description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
