# test_call.py

from tnt_api import call_time_in_transit_api

test_payload = {
    "originCountryCode": "CA",
    "originStateProvince": "QC",
    "originCityName": "Boucherville",
    "originPostalCode": "J4B6H5",
    "destinationCountryCode": "US",
    "destinationStateProvince": "NH",
    "destinationCityName": "MANCHESTER",
    "destinationPostalCode": "03104",
    "weight": "10.5",
    "weightUnitOfMeasure": "LBS",
    "shipmentContentsValue": "10.5",
    "shipmentContentsCurrencyCode": "USD",
    "billType": "03",
    "shipDate": "2025-03-27",
    "avvFlag": True,
    "numberOfPackages": "1"
}

result = call_time_in_transit_api(test_payload)

if result:
    print(result)
