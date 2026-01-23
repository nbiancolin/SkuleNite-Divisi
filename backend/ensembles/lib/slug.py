from django.utils.text import slugify

def generate_unique_slug(model_class, value, instance=None):
    """
    Generates a unique slug for a model instance.
    """
    base_slug = slugify(value)
    slug = base_slug
    counter = 1

    # Exclude current instance if updating
    queryset = model_class.objects.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug