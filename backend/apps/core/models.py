import uuid

from django.db import models


class PublicModel(models.Model):
    """Base for models exposed through the API: clients only ever see the opaque `public_id`."""

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
