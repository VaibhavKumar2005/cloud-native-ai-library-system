import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_backend.settings')
django.setup()

from django.contrib.auth import authenticate

# Test testuser
user = authenticate(username='testuser', password='testpass123')
if user:
    print(f'✅ testuser authentication SUCCESS')
    print(f'   User ID: {user.id}')
    print(f'   Username: {user.username}')
    print(f'   Is Active: {user.is_active}')
else:
    print('❌ testuser authentication FAILED')

# Test root user
user2 = authenticate(username='root', password='rootpass123')
if user2:
    print(f'✅ root authentication SUCCESS (password: rootpass123)')
else:
    print('❌ root authentication FAILED (password might be different)')
