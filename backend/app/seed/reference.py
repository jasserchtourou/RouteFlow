"""Static reference data for the seed: real places, plausible fictional companies/products."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WarehouseSpec:
    code: str
    name: str
    city: str
    latitude: float
    longitude: float
    capacity: int
    utilization_pct: int
    status: str


WAREHOUSES = [
    WarehouseSpec("WH-HAN", "Hannover Central DC", "Hannover", 52.4227, 9.7341, 48000, 78, "OPERATIONAL"),
    WarehouseSpec("WH-GAR", "Garbsen Logistics Park", "Garbsen", 52.4220, 9.5970, 36000, 96, "DISRUPTED"),
    WarehouseSpec("WH-LAN", "Langenhagen Cargo Hub", "Langenhagen", 52.4510, 9.7370, 22000, 71, "OPERATIONAL"),
    WarehouseSpec("WH-HAM", "Hamburg Port DC", "Hamburg", 53.5200, 10.0000, 60000, 88, "CONGESTED"),
    WarehouseSpec("WH-BER", "Berlin Spandau Hub", "Berlin", 52.5360, 13.2000, 52000, 64, "OPERATIONAL"),
    WarehouseSpec("WH-LEJ", "Leipzig Air Cargo DC", "Leipzig", 51.4240, 12.2360, 44000, 69, "OPERATIONAL"),
    WarehouseSpec("WH-KAS", "Kassel Regional DC", "Kassel", 51.3127, 9.4797, 28000, 58, "OPERATIONAL"),
]  # fmt: skip

# City -> (latitude, longitude); used for delivery locations and vehicle positions.
CITIES = {
    "Hannover": (52.3759, 9.7320),
    "Garbsen": (52.4220, 9.5970),
    "Langenhagen": (52.4510, 9.7370),
    "Hamburg": (53.5511, 9.9937),
    "Berlin": (52.5200, 13.4050),
    "Leipzig": (51.3397, 12.3731),
    "Kassel": (51.3127, 9.4797),
    "Bremen": (53.0793, 8.8017),
    "Braunschweig": (52.2689, 10.5268),
    "Göttingen": (51.5413, 9.9158),
    "Magdeburg": (52.1205, 11.6276),
    "Dortmund": (51.5136, 7.4653),
}

# (origin city, destination city, distance km, duration minutes)
LANES = [
    ("Hannover", "Hamburg", 155, 120),
    ("Hannover", "Berlin", 285, 190),
    ("Hannover", "Braunschweig", 65, 55),
    ("Hannover", "Bremen", 125, 95),
    ("Garbsen", "Hannover", 18, 30),
    ("Garbsen", "Göttingen", 130, 100),
    ("Langenhagen", "Hannover", 12, 25),
    ("Langenhagen", "Magdeburg", 135, 105),
    ("Hamburg", "Bremen", 125, 95),
    ("Hamburg", "Hannover", 155, 120),
    ("Berlin", "Leipzig", 190, 130),
    ("Berlin", "Magdeburg", 150, 110),
    ("Leipzig", "Kassel", 275, 190),
    ("Kassel", "Göttingen", 50, 45),
    ("Kassel", "Dortmund", 165, 125),
    ("Kassel", "Hannover", 165, 120),
]  # fmt: skip

CUSTOMERS = [
    "Nordstahl Handels GmbH", "Weserland Foods AG", "Leinetal Pharma GmbH", "Harz Elektronik KG",
    "Elbe Fresh Market", "Hansa Auto Parts GmbH", "Märkische Baustoffe", "Sachsen Medizintechnik",
    "Calenberg Getränke", "Nordwest Retail Group", "Kasseler Maschinenbau AG", "Heide Bio Logistik",
    "Lüneburger Kosmetik", "Brocken Outdoor GmbH", "Rhein-Ruhr Großhandel",
]  # fmt: skip

CARRIERS = ["RouteFlow Fleet", "Nordtrans", "Hansa Cargo", "KS Express"]

# (sku, product name, temperature controlled, typical reorder threshold)
PRODUCTS = [
    ("EL-1001", "Industrial Sensor Module", False, 200),
    ("EL-1002", "Lithium Battery Pack 48V", False, 150),
    ("EL-1003", "Control Unit PLC-7", False, 80),
    ("AU-2001", "Brake Disc Set", False, 300),
    ("AU-2002", "Oil Filter Carton", False, 500),
    ("AU-2003", "LED Headlight Assembly", False, 120),
    ("FD-3001", "Frozen Vegetable Pallet", True, 100),
    ("FD-3002", "Chilled Dairy Crate", True, 250),
    ("FD-3003", "Fresh Salad Box", True, 300),
    ("PH-4001", "Insulin Pens (2-8°C)", True, 60),
    ("PH-4002", "Vaccine Cool-Box", True, 40),
    ("RT-5001", "Packaged Beverages Pallet", False, 400),
    ("RT-5002", "Household Cleaning Set", False, 350),
    ("RT-5003", "Cosmetics Display Unit", False, 180),
    ("BM-6001", "Cement Bags (25 kg)", False, 600),
    ("BM-6002", "Steel Reinforcement Bundle", False, 90),
]  # fmt: skip

VEHICLE_PREFIXES = {"Hannover": "H", "Hamburg": "HH", "Berlin": "B", "Leipzig": "L", "Kassel": "KS"}

DRIVER_NAMES = [
    "Jonas Becker", "Lena Hoffmann", "Murat Yilmaz", "Katarzyna Nowak", "Felix Brandt",
    "Sabine Krüger", "Tobias Wendt", "Aylin Demir", "Marco Rossi", "Hanna Lindqvist",
    "Dennis Voigt", "Petra Schade", "Ibrahim Haddad", "Svenja Lorenz", "Jakub Kowalski",
    "Nina Albrecht", "Stefan Probst", "Olga Petrova", "Markus Heine", "Julia Winter",
    "Kerem Aksoy", "Anja Fuchs", "Lukas Reimann", "Mira Hartmann",
]  # fmt: skip
