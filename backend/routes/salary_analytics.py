"""
Salary Analytics — aggregates salary data for the Indian job market.
Provides breakdowns by role, location, and experience level.

All figures are annual INR (₹). Benchmarks reflect typical Indian tech
industry compensation (2025-26) and are meant as realistic guidance,
not exact offers — actual pay varies by company tier, funding, and
negotiation.
"""

from fastapi import APIRouter, Query
from typing import Optional


router = APIRouter(prefix="/api/salary", tags=["salary-analytics"])

CURRENCY = "INR"
LPA = 100_000  # 1 lakh = ₹1,00,000


def _lpa(min_l: float, max_l: float, med_l: float) -> dict:
    """Benchmarks are authored in lakhs per annum for readability."""
    return {
        "min": int(min_l * LPA),
        "max": int(max_l * LPA),
        "median": int(med_l * LPA),
    }


# Curated salary benchmarks by role category (India market, annual INR)
SALARY_BENCHMARKS = {
    "Software Engineer": {
        "junior": _lpa(4, 9, 6),
        "mid": _lpa(10, 22, 15),
        "senior": _lpa(22, 45, 32),
        "lead": _lpa(40, 75, 55),
    },
    "Frontend Developer": {
        "junior": _lpa(3.5, 8, 5.5),
        "mid": _lpa(8, 18, 12),
        "senior": _lpa(18, 38, 26),
        "lead": _lpa(35, 65, 45),
    },
    "Backend Developer": {
        "junior": _lpa(4, 9, 6),
        "mid": _lpa(10, 20, 14),
        "senior": _lpa(20, 42, 30),
        "lead": _lpa(38, 70, 50),
    },
    "Data Scientist": {
        "junior": _lpa(5, 10, 7),
        "mid": _lpa(12, 24, 17),
        "senior": _lpa(25, 50, 35),
        "lead": _lpa(45, 80, 60),
    },
    "DevOps Engineer": {
        "junior": _lpa(4, 8, 5.5),
        "mid": _lpa(9, 20, 13),
        "senior": _lpa(20, 40, 28),
        "lead": _lpa(38, 68, 48),
    },
    "Product Manager": {
        "junior": _lpa(8, 15, 10),
        "mid": _lpa(15, 30, 22),
        "senior": _lpa(30, 55, 40),
        "lead": _lpa(50, 90, 65),
    },
    "UX Designer": {
        "junior": _lpa(3, 7, 4.5),
        "mid": _lpa(7, 15, 10),
        "senior": _lpa(15, 30, 20),
        "lead": _lpa(28, 50, 36),
    },
    "ML Engineer": {
        "junior": _lpa(6, 12, 8),
        "mid": _lpa(14, 30, 20),
        "senior": _lpa(30, 60, 42),
        "lead": _lpa(55, 100, 70),
    },
}

# Location multipliers (relative to India average) for major tech hubs
LOCATION_MULTIPLIERS = {
    "Bengaluru": 1.15,
    "Mumbai": 1.10,
    "Gurugram": 1.08,
    "Noida": 1.02,
    "Hyderabad": 1.05,
    "Pune": 1.00,
    "Chennai": 0.98,
    "Kolkata": 0.90,
    "Ahmedabad": 0.88,
    "Jaipur": 0.82,
    "Remote": 1.00,
}


@router.get("/benchmarks")
def get_salary_benchmarks(
    role: Optional[str] = Query(None, max_length=100),
    location: Optional[str] = Query(None, max_length=100),
):
    """Get salary benchmarks by role and location (annual INR)."""
    roles = SALARY_BENCHMARKS.keys()
    if role:
        # Fuzzy match
        matched = [r for r in roles if role.lower() in r.lower()]
        if matched:
            roles = matched

    result = {}
    for role_name in roles:
        data = SALARY_BENCHMARKS[role_name]
        loc_mult = LOCATION_MULTIPLIERS.get(location, 1.0) if location else 1.0

        adjusted = {}
        for level, salaries in data.items():
            adjusted[level] = {
                "min": round(salaries["min"] * loc_mult),
                "max": round(salaries["max"] * loc_mult),
                "median": round(salaries["median"] * loc_mult),
            }

        result[role_name] = adjusted

    return {
        "roles": result,
        "location": location or "India Average",
        "multiplier": LOCATION_MULTIPLIERS.get(location, 1.0) if location else 1.0,
        "currency": CURRENCY,
    }


@router.get("/compare")
def compare_salaries(
    roles: str = Query("", max_length=300, description="Comma-separated roles"),
    location: str = Query("", max_length=100, description="Location"),
):
    """Compare salaries across multiple roles (annual INR)."""
    role_list = [r.strip() for r in roles.split(",") if r.strip()] if roles else list(SALARY_BENCHMARKS.keys())[:4]
    loc_mult = LOCATION_MULTIPLIERS.get(location, 1.0) if location else 1.0

    comparison = []
    for role in role_list:
        matched = [r for r in SALARY_BENCHMARKS if role.lower() in r.lower()]
        if matched:
            role_data = SALARY_BENCHMARKS[matched[0]]
            mid = role_data["mid"]
            comparison.append({
                "role": matched[0],
                "junior_median": round(role_data["junior"]["median"] * loc_mult),
                "mid_median": round(mid["median"] * loc_mult),
                "senior_median": round(role_data["senior"]["median"] * loc_mult),
                "lead_median": round(role_data["lead"]["median"] * loc_mult),
            })

    return {
        "comparison": comparison,
        "location": location or "India Average",
        "currency": CURRENCY,
    }


@router.get("/locations")
def get_location_data():
    """Get all available locations with their pay multipliers."""
    return {
        "locations": [
            {"name": loc, "multiplier": mult}
            for loc, mult in sorted(LOCATION_MULTIPLIERS.items(), key=lambda x: -x[1])
        ],
        "currency": CURRENCY,
    }
