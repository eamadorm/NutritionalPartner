import sys

sys.path.append(".")
from backend.smae_engine.source_code.main import SMAEEngine

engine = SMAEEngine()
uri = "gs://nutritional-data-sources/SMAE.pdf"
count = engine._get_page_count(uri)
print(f"Total pages: {count}")
