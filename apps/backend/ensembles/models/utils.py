from logging import getLogger

from django.core.files.storage import default_storage

logger = getLogger("app")

class DeleteFilesMixin:
    """
    Base class to be added to a model that on delete, cleans up associated file keys
    """    

    keys_to_delete: list[str]

    def delete(self, **kwargs):
        if not getattr(self, "keys_to_delete", None):
            raise ValueError(
                "Model with DeleteFilesMixin must define `keys_to_delete`"
            )

        for key in self.keys_to_delete:
            value = getattr(self, key)
            try:
                if default_storage.exists(value):
                    default_storage.delete(value)
                    logger.info(f"Deleted file: {value}")
                else:
                    logger.warning(f"File does not exist, skipping: {value}")
            except Exception as e:
                logger.error(f"Failed to delete {value}: {e}")
        
        super().delete(**kwargs)