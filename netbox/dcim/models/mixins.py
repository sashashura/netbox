from django.db import models
from dcim.choices import *
from utilities.utils import to_kilograms


class DeviceWeightMixin(models.Model):
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True
    )
    weight_unit = models.CharField(
        max_length=50,
        choices=DeviceWeightUnitChoices,
        blank=True,
    )
    # Stores the normalized length (in meters) for database ordering
    _abs_weight = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):

        # Store the given weight (if any) in meters for use in database ordering
        if self.weight and self.weight_unit:
            self._abs_weight = to_kilograms(self.weight, self.weight_unit)
        else:
            self._abs_weight = None

        super().save(*args, **kwargs)
