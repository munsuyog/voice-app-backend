import httpx
import osm2geojson

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

async def fetch_overpass(query: str) -> dict:
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            OVERPASS_URL,
            data={
                "data": query.strip()
            }
        )
        response.raise_for_status()
        return response.json()

def convert_to_geojson(overpass_json: dict) -> dict:
    return osm2geojson.json2geojson(overpass_json)

async def overpass_to_geojson(query: str) -> dict:
    print(query)
    overpass_json = await fetch_overpass(query)
    return convert_to_geojson(overpass_json)
