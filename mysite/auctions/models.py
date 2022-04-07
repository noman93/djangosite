from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.


class User(AbstractUser):
    pass


class Auction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=220, null=True)
    image_url = models.URLField(max_length=600, default=None)
    price = models.DecimalField(decimal_places=2, max_digits=100, default=None)
    date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateField()
    status = models.CharField(max_length=6, default="Open")
    highest_bid = models.DecimalField(
        decimal_places=2, max_digits=100, null=True, default=0)
    highest_bidder = models.CharField(max_length=200, default=None, blank=True)

    def __str__(self):
        return self.title
