from pathlib import Path
import yaml
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "banks.yaml"
banks = {"ing": [],"kbc": [],"belfius": [],"bnp": []}

with open(
    CONFIG_PATH,
    "r",
    encoding="utf-8",
) as file:

    config = yaml.safe_load(file)
    b = config.get("banks")

    for bank in banks:
        bank_object = b.get(bank)
        sitemaps_bank = bank_object.get("sitemap_urls")

        for sitemap in sitemaps_bank:
            response = requests.get(sitemap)
            
            banks[bank] =



output_path = PROJECT_ROOT / "config" / "links.txt"
with open(output_path, "w",encoding="utf-8") as file:
