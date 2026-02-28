from typing import Dict, List


def evaluate_schemes(profile: Dict) -> List[Dict]:
    """
    Determine eligible financial inclusion schemes
    based on a simple user profile.

    profile keys:
        age: int
        income: int (monthly)
        occupation: str
        gender: str
        rural: bool
        bank_account: bool
        farmer: bool
        business_owner: bool
    """

    age = profile.get("age")
    income = profile.get("income", 0)
    occupation = profile.get("occupation", "").lower()
    gender = profile.get("gender", "").lower()
    rural = profile.get("rural", False)
    bank_account = profile.get("bank_account", True)
    farmer = profile.get("farmer", False)
    business_owner = profile.get("business_owner", False)

    schemes = []

    # PM Jan Dhan Yojana
    if not bank_account:
        schemes.append({
            "name": "Pradhan Mantri Jan Dhan Yojana",
            "reason": "You do not have a bank account.",
            "benefit": "Free zero-balance bank account with debit card and DBT benefits.",
            "cost": "Free",
            "next_step": "Visit nearest bank or Business Correspondent to open an account."
        })

    # PMSBY Accident Insurance
    if age and 18 <= age <= 70:
        schemes.append({
            "name": "Pradhan Mantri Suraksha Bima Yojana",
            "reason": "Available for individuals aged 18–70.",
            "benefit": "₹2 lakh accident insurance coverage.",
            "cost": "₹20 per year",
            "next_step": "Enroll through your bank account."
        })

    # PMJJBY Life Insurance
    if age and 18 <= age <= 50:
        schemes.append({
            "name": "Pradhan Mantri Jeevan Jyoti Bima Yojana",
            "reason": "Available for individuals aged 18–50.",
            "benefit": "₹2 lakh life insurance coverage.",
            "cost": "₹436 per year",
            "next_step": "Enroll via your bank branch."
        })

    # Atal Pension Yojana
    if age and 18 <= age <= 40:
        schemes.append({
            "name": "Atal Pension Yojana",
            "reason": "Available for individuals aged 18–40.",
            "benefit": "Guaranteed monthly pension after age 60.",
            "cost": "Contribution starts around ₹210/month.",
            "next_step": "Apply through your bank."
        })

    # Mudra Loan
    if business_owner or occupation in ["self-employed", "vendor", "shopkeeper"]:
        schemes.append({
            "name": "Pradhan Mantri Mudra Yojana",
            "reason": "Supports small businesses and self-employed workers.",
            "benefit": "Loans up to ₹10 lakh for business growth.",
            "cost": "Interest varies by bank.",
            "next_step": "Apply at bank with business details."
        })

    # Stand-Up India
    if gender == "female" and business_owner:
        schemes.append({
            "name": "Stand-Up India Scheme",
            "reason": "Supports women entrepreneurs.",
            "benefit": "Loans from ₹10 lakh to ₹1 crore for new businesses.",
            "cost": "Bank loan with applicable interest.",
            "next_step": "Apply through scheduled bank."
        })

    # Kisan Credit Card
    if farmer:
        schemes.append({
            "name": "Kisan Credit Card",
            "reason": "Available for farmers.",
            "benefit": "Low-interest credit for agricultural needs.",
            "cost": "Subsidized interest rates.",
            "next_step": "Apply at your nearest bank branch."
        })

    return schemes