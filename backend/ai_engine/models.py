from django.db import models

class Document(models.Model):
    title = models.CharField(max_length=200)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='pdfs/')  # This saves the actual file
    processed = models.BooleanField(default=False)  # Has the AI read this yet?

    def __str__(self):
        return self.title