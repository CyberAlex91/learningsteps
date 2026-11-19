# Zweck: Fragt öffentliche Azure-Listenpreise für die gewählte AKS-VM-Größe ab.
"""Read public EUR VM list prices; no Azure login or resource changes."""

import json
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen


def main():
    filters = (
        "serviceName eq 'Virtual Machines' and "
        "armRegionName eq 'germanywestcentral' and "
        "armSkuName eq 'Standard_D4s_v6' and priceType eq 'Consumption'"
    )
    url = "https://prices.azure.com/api/retail/prices?" + urlencode(
        {"currencyCode": "'EUR'", "$filter": filters}
    )
    matches = []
    for _ in range(10):
        if urlparse(url).hostname != "prices.azure.com":
            raise RuntimeError("Unexpected price API hostname")
        with urlopen(url, timeout=30) as response:
            page = json.load(response)
        for item in page.get("Items", []):
            label = " ".join(str(item.get(key, "")) for key in
                             ("productName", "skuName", "meterName")).lower()
            if any(word in label for word in ("windows", "spot", "low priority")):
                continue
            if item.get("type") != "Consumption" or not item.get("isPrimaryMeterRegion"):
                continue
            if item.get("currencyCode") != "EUR" or item.get("unitOfMeasure") != "1 Hour":
                raise RuntimeError("Unexpected currency or billing unit")
            price = item["retailPrice"]
            matches.append({
                "VM": item["armSkuName"], "Region": item["armRegionName"],
                "Product": item["productName"], "Meter": item["meterName"],
                "Currency": "EUR", "OneNodePerHour": price,
                "TwoNodesPerHour": round(price * 2, 4),
                "TwoNodesPer24Hours": round(price * 2 * 24, 2),
                "TwoNodesPer730Hours": round(price * 2 * 730, 2),
                "EffectiveFrom": item.get("effectiveStartDate"),
            })
        url = page.get("NextPageLink")
        if not url:
            break
    else:
        raise RuntimeError("Price API pagination limit exceeded")
    if not matches:
        raise RuntimeError("No matching regular Linux EUR hourly price found")
    print(json.dumps(matches, indent=2))
    print("VM compute list price only: excludes disks, IPs, load balancer, data transfer,")
    print("ACR, PostgreSQL, Key Vault and applicable taxes/contract adjustments.")


if __name__ == "__main__":
    main()
