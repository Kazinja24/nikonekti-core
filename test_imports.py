#!/usr/bin/env python
import sys
import os

# Set up environment
base_path = r"E:\NIKONEKTI NYUMBA\nikonekti_backend"
sys.path.insert(0, base_path)
os.chdir(base_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nikonekti_backend.settings.development')

try:
    print("Step 1: Importing django...")
    import django
    print("✓ Django imported")
    
    print("Step 2: Setting up Django...")
    django.setup()
    print("✓ Django setup complete")
    
    print("Step 3: Running makemigrations...")
    from django.core.management import call_command
    call_command('makemigrations', verbosity=2)
    print("✓ Makemigrations complete")
    
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
