"""Pre-management initial locations retained for compatibility regression tests."""
from .models import Branch


def ensure_legacy_initial_location(business):
    existing = Branch.objects.filter(business=business).first()
    if existing is not None:
        return existing
    return Branch.objects.create(business=business, name=business.name,
        address=business.address, phone=business.phone, uses_business_defaults=True)
