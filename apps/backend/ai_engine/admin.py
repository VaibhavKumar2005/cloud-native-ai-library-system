from django.contrib import admin
from .models import Document, ExternalAuthIdentity, OAuthExchangeCode

# This registers the "Documents" table so you can see it in the Admin Panel
admin.site.register(Document)
admin.site.register(ExternalAuthIdentity)
admin.site.register(OAuthExchangeCode)
