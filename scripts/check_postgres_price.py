"""Read public PostgreSQL Flexible Server price candidates in EUR; no Azure writes."""

import json
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen


def main():
    filters = (
        "serviceName eq 'Azure Database for PostgreSQL' and "
        "armRegionName eq 'westeurope' and priceType eq 'Consumption'"
    )
    url = "https://prices.azure.com/api/retail/prices?" + urlencode(
        {"currencyCode": "'EUR'", "$filter": filters}
    )
    matches = []
    for _ in range(15):
        if urlparse(url).hostname != "prices.azure.com":
            raise RuntimeError("Unexpected pricing hostname")
        with urlopen(url, timeout=30) as response:
            page = json.load(response)
        for item in page.get("Items", []):
            product = str(item.get("productName", "")).lower()
            if "flexible server" not in product and "flex server" not in product:
                continue
            selected = (
                item.get("skuName") == "B1MS"
                or (item.get("skuName") == "Storage" and item.get("meterName") == "Storage Data Stored")
                or item.get("skuName") == "Backup Storage LRS"
            )
            if not selected:
                continue
            if item.get("type") != "Consumption" or not item.get("isPrimaryMeterRegion"):
                continue
            if item.get("currencyCode") != "EUR":
                raise RuntimeError("Unexpected currency")
            matches.append({key: item.get(key) for key in (
                "productName", "skuName", "meterName", "retailPrice",
                "currencyCode", "unitOfMeasure", "effectiveStartDate",
            )})
        url = page.get("NextPageLink")
        if not url:
            break
    else:
        raise RuntimeError("Price pagination limit exceeded")
    if not matches:
        raise RuntimeError("No matching flexible-server price candidates found")
    print(json.dumps(matches, indent=2))
    print("Candidates only: billing units and storage/backup type require review.")
    print("Excludes inter-region peering/transfer, other services and contract/tax adjustments.")


if __name__ == "__main__":
    main()
