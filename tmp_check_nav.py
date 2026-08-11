from config import settings
from services.providers.brs_provider import BrsProvider
provider = BrsProvider()
nav = provider.get_nav("عیار")
print(f"NAV object: {nav}")
print(f"issue_nav: {nav.issue_nav}")
print(f"redeem_nav: {nav.redeem_nav}")