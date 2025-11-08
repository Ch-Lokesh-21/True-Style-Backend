from fastapi import APIRouter, HTTPException, Depends
import httpx
from typing import Dict
from app.api.deps import get_current_user
router = APIRouter()


@router.get("/{pincode}", dependencies=[Depends(get_current_user)])
async def get_location(pincode: int)->Dict:
    if pincode<100000 or pincode>999999:
        raise HTTPException(status_code=422, detail="Invalid Pincode")
    url = f"https://api.postalpincode.in/pincode/{pincode}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch data from postal API")

    data = response.json()

    # API returns a list with one element
    if not data or data[0]["Status"] != "Success":
        raise HTTPException(status_code=404, detail="Invalid PIN code or data not found")

    post_office = data[0]["PostOffice"][0]
    city = post_office.get("District")
    state = post_office.get("State")
    country = post_office.get("Country")

    return {
        "pincode": pincode,
        "city": city,
        "state": state,
        "country": country
    }