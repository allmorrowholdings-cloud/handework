from decimal import Decimal

# Server-authoritative prices. The browser sends only product IDs and quantities.
PRODUCTS = {
    "plumb-kit": {"name": "Plumber essential kit", "category": "Plumbing", "price": Decimal("780.00")},
    "plumb-pro": {"name": "Pipe & fitting pro set", "category": "Plumbing", "price": Decimal("420.00")},
    "elec-kit": {"name": "Electrician safety kit", "category": "Electrical", "price": Decimal("690.00")},
    "elec-meter": {"name": "handEwork digital multimeter", "category": "Electrical", "price": Decimal("295.00")},
    "beauty-kit": {"name": "Hair professional kit", "category": "Hairdressing", "price": Decimal("620.00")},
    "makeup-kit": {"name": "Makeup artist field kit", "category": "Makeup", "price": Decimal("540.00")},
    "tailor-kit": {"name": "Tailoring precision kit", "category": "Tailoring", "price": Decimal("485.00")},
    "tailor-case": {"name": "Mobile tailoring tool case", "category": "Tailoring", "price": Decimal("230.00")},
    "carp-kit": {"name": "Carpenter measure & finish kit", "category": "Carpentry", "price": Decimal("740.00")},
    "carp-measure": {"name": "handEwork tape & marking set", "category": "Carpentry", "price": Decimal("160.00")},
    "weld-kit": {"name": "Welder protection & torch kit", "category": "Welding", "price": Decimal("890.00")},
    "weld-glove": {"name": "Heat-resistant welding gloves", "category": "Welding", "price": Decimal("125.00")},
    "paint-kit": {"name": "Painter prep & finish kit", "category": "Painting", "price": Decimal("465.00")},
    "paint-pro": {"name": "Roller, brush & masking set", "category": "Painting", "price": Decimal("185.00")},
    "mason-kit": {"name": "Mason layout & finishing kit", "category": "Masonry", "price": Decimal("590.00")},
    "mason-hand": {"name": "Trowel, float & line set", "category": "Masonry", "price": Decimal("210.00")},
    "food-kit": {"name": "Catering service kit", "category": "Catering", "price": Decimal("560.00")},
    "food-uniform": {"name": "Chef jacket & apron set", "category": "Catering", "price": Decimal("210.00")},
    "digital-kit": {"name": "Digital creator field kit", "category": "Digital & design", "price": Decimal("980.00")},
    "digital-desk": {"name": "Designer desk essentials", "category": "Digital & design", "price": Decimal("320.00")},
}
