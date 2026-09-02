# ==========================
# dataset_generator.py
# ==========================

import random
import numpy as np
import pandas as pd
from pathlib import Path

from config import (
    STATE_CITY_MAP, STATE_MULTIPLIERS,
    REGION_TYPES, REGION_MULTIPLIER,
    SEASONS, SEASON_MULTIPLIER,
    RENOVATION_TYPES, QUALITY_FACTORS,
    MATERIAL_QUALITY, BASE_PRICES,
    BASE_LABOUR_RATE,
    random_state, random_city
)

random.seed(42)
np.random.seed(42)

BASE_DIR    = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
DATASET_DIR.mkdir(exist_ok=True)


class HouseRenovationDatasetGenerator:

    def __init__(self):
        self.records = []

    # ─────────────────────────────────────────
    # House Details
    # ─────────────────────────────────────────
    def generate_house_details(self):

        area      = random.randint(400, 6000)

        rooms     = max(1, min(8,
                    round(area / 450) + random.randint(-1, 1)))

        bathrooms = max(1, min(6,
                    rooms // 2 + random.randint(0, 1)))

        if area < 1200:
            floors = 1
        elif area < 2500:
            floors = random.choice([1, 2])
        elif area < 4000:
            floors = random.choice([2, 3])
        else:
            floors = random.choice([3, 4])

        age      = random.randint(1, 80)
        basement = random.choice([0, 1])

        return area, rooms, bathrooms, floors, age, basement

    # ─────────────────────────────────────────
    # Location Details
    # ─────────────────────────────────────────
    def generate_location_details(self):

        state  = random_state()
        city   = random_city(state)

        region = random.choices(
            REGION_TYPES,
            weights=[50, 30, 20], k=1)[0]

        season = random.choice(SEASONS)

        renovation_type = random.choice(
            list(RENOVATION_TYPES.keys()))

        quality_grade = random.choices(
            list(QUALITY_FACTORS.keys()),
            weights=[30, 40, 20, 10], k=1)[0]

        material_quality = random.choices(
            MATERIAL_QUALITY,
            weights=[30, 50, 20], k=1)[0]

        return (state, city, region, season,
                renovation_type, quality_grade,
                material_quality)

    # ─────────────────────────────────────────
    # Condition Scores (1–10 numeric)
    # ─────────────────────────────────────────
    def generate_condition_scores(self, age):

        base       = max(2, 10 - age // 10)
        wall       = max(1, min(10, base + random.randint(-2, 2)))
        roof       = max(1, min(10, base + random.randint(-2, 2)))
        plumbing   = max(1, min(10, base + random.randint(-2, 2)))
        electrical = max(1, min(10, base + random.randint(-2, 2)))

        return wall, roof, plumbing, electrical

    # ─────────────────────────────────────────
    # Waterproofing
    # ─────────────────────────────────────────
    def generate_waterproofing(self, season, roof, wall):

        prob = 0.20
        if season == "Monsoon": prob += 0.35
        if roof   <= 4:         prob += 0.25
        if wall   <= 4:         prob += 0.20

        return "Yes" if random.random() < prob else "No"

    # ─────────────────────────────────────────
    # Material Prices
    # ─────────────────────────────────────────
    def generate_material_prices(self, state, quality_grade):

        state_mult   = STATE_MULTIPLIERS[state]["material"]
        quality_mult = QUALITY_FACTORS[quality_grade]
        prices       = {}

        for mat, base in BASE_PRICES.items():
            variation   = random.uniform(0.95, 1.05)
            prices[mat] = round(
                base * state_mult * quality_mult * variation, 2)

        return (prices["Cement"], prices["Steel"],
                prices["Sand"],   prices["Paint"],
                prices["Brick"],  prices["Tile"],
                prices["Wood"])

    # ─────────────────────────────────────────
    # Calculate All Targets
    # ─────────────────────────────────────────
    def calculate_targets(
            self, area, age, wall, roof, plumbing, electrical,
            state, region, season, renovation_type, quality_grade,
            basement, waterproofing, cement, steel, sand,
            paint, brick, tile, wood):

        state_material = STATE_MULTIPLIERS[state]["material"]
        state_labour = STATE_MULTIPLIERS[state]["labour"]
        region_mult = REGION_MULTIPLIER[region]
        season_cost = SEASON_MULTIPLIER[season]["cost"]
        season_duration = SEASON_MULTIPLIER[season]["duration"]
        quality_factor = QUALITY_FACTORS[quality_grade]
        base_days = RENOVATION_TYPES[renovation_type]["days"]

        # Real-world renovation-specific scope. Only relevant conditions and
        # materials influence each renovation type.
        specs = {
            "Full House Renovation": (1.00, [cement, steel, sand, paint, brick, tile, wood], [wall, roof, plumbing, electrical], 1.00),
            "Interior Renovation": (0.70, [paint, wood, cement, sand], [wall], 0.72),
            "Exterior Renovation": (0.55, [paint, cement, sand, brick], [wall, roof], 0.62),
            "Kitchen Renovation": (0.12, [wood, tile, cement, paint], [plumbing, electrical, wall], 0.85),
            "Bathroom Renovation": (0.08, [tile, cement, sand, paint], [plumbing, wall], 0.95),
            "Painting": (0.82, [paint, cement, sand], [wall], 0.45),
            "Flooring & Tiling": (0.78, [tile, cement, sand], [wall], 0.55),
            "Roofing": (0.60, [cement, steel, sand, brick], [roof], 0.80),
            "Plumbing": (0.10, [cement, sand, tile], [plumbing], 1.05),
            "Electrical Work": (0.45, [cement, steel], [electrical], 0.78),
        }
        coverage, relevant_prices, relevant_conditions, labour_intensity = specs.get(
            renovation_type, (0.60, [cement, steel, sand, paint], [wall], 0.75)
        )
        effective_area = max(60, area * coverage)
        avg_condition = sum(relevant_conditions) / len(relevant_conditions)
        condition_factor = 1 + (10 - avg_condition) / 8
        avg_mat_price = sum(relevant_prices) / len(relevant_prices)

        # Area-based cost is deliberately scaled by the selected renovation scope.
        material_cost = effective_area * avg_mat_price * 0.32 * quality_factor * state_material
        labour_cost = (effective_area * BASE_LABOUR_RATE * labour_intensity *
                       condition_factor * state_labour * region_mult * season_cost)

        # Type-specific extras reflect realistic work requirements.
        extras = 0
        if renovation_type == "Roofing" and waterproofing == "Yes": extras += 18000
        if renovation_type == "Exterior Renovation" and waterproofing == "Yes": extras += 12000
        if renovation_type == "Bathroom Renovation": extras += 7000
        if renovation_type == "Kitchen Renovation": extras += 15000
        if renovation_type == "Full House Renovation":
            extras += (18000 if basement == 1 else 0) + (12000 if waterproofing == "Yes" else 0)
        if renovation_type == "Plumbing": extras += (10 - plumbing) * 1800
        if renovation_type == "Electrical Work": extras += (10 - electrical) * 1500

        duration = (base_days + effective_area / 140 + (10 - avg_condition) * 2.5 + age * 0.08)
        duration *= season_duration

        labour_variation = np.clip(np.random.normal(1.0, 0.10), 0.75, 1.25)
        project_variation = np.clip(np.random.normal(1.0, 0.10), 0.75, 1.30)
        labour_cost *= labour_variation
        total_cost = max(15000, (material_cost + labour_cost + extras) * project_variation)
        duration = max(3, min(500, round(duration + np.random.normal(0, max(2, duration * 0.06)))))

        planned = material_cost + (effective_area * BASE_LABOUR_RATE * labour_intensity * state_labour * region_mult) + extras
        owner_budget = planned * random.uniform(1.05, 1.25)
        budget_status = "Within Budget" if total_cost <= owner_budget else "Over Budget"
        return round(labour_cost, 2), duration, round(total_cost, 2), budget_status

    # ─────────────────────────────────────────
    # Generate One Record
    # ─────────────────────────────────────────
    def generate_record(self):

        (area, rooms, bathrooms,
         floors, age, basement) = self.generate_house_details()

        (state, city, region, season,
         renovation_type, quality_grade,
         material_quality) = self.generate_location_details()

        wall, roof, plumbing, electrical = \
            self.generate_condition_scores(age)

        waterproofing = self.generate_waterproofing(
            season, roof, wall)

        (cement, steel, sand,
         paint,  brick, tile, wood) = \
            self.generate_material_prices(state, quality_grade)

        (labour_cost, duration,
         renovation_cost, budget_status) = self.calculate_targets(
            area, age,
            wall, roof, plumbing, electrical,
            state, region, season,
            renovation_type, quality_grade,
            basement, waterproofing,
            cement, steel, sand,
            paint,  brick, tile, wood)

        return {
            "House_Area_sqft"        : area,
            "Number_of_Rooms"        : rooms,
            "Number_of_Bathrooms"    : bathrooms,
            "Number_of_Floors"       : floors,
            "House_Age"              : age,
            "Basement"               : basement,
            "State"                  : state,
            "City"                   : city,
            "Region_Type"            : region,
            "Renovation_Type"        : renovation_type,
            "Quality_Grade"          : quality_grade,
            "Material_Quality"       : material_quality,
            "Wall_Condition"         : wall,
            "Roof_Condition"         : roof,
            "Plumbing_Condition"     : plumbing,
            "Electrical_Condition"   : electrical,
            "Waterproofing_Required" : waterproofing,
            "Season"                 : season,
            "Cement_Price"           : cement,
            "Steel_Price"            : steel,
            "Sand_Price"             : sand,
            "Paint_Price"            : paint,
            "Brick_Price"            : brick,
            "Tile_Price"             : tile,
            "Wood_Price"             : wood,
            "Estimated_Labour_Cost"     : labour_cost,
            "Estimated_Duration_Days"   : duration,
            "Estimated_Renovation_Cost" : renovation_cost,
            "Budget_Status"             : budget_status,
        }

    # ─────────────────────────────────────────
    # Generate Full Dataset
    # ─────────────────────────────────────────
    def generate_dataset(self, num_records=20000):

        print("=" * 55)
        print("   HOUSE RENOVATION DATASET GENERATOR")
        print("=" * 55)
        print(f"\n  Generating {num_records:,} records...\n")

        self.records = []

        for i in range(num_records):
            self.records.append(self.generate_record())
            if (i + 1) % 2000 == 0:
                print(f"  ✅ {i+1:,} records generated...")

        df = pd.DataFrame(self.records)
        return df

    # ─────────────────────────────────────────
    # Validate Dataset
    # ─────────────────────────────────────────
    def validate_dataset(self, df):

        print("\n" + "=" * 55)
        print("   DATASET VALIDATION REPORT")
        print("=" * 55)

        print(f"\n  Total Rows        : {len(df):,}")
        print(f"  Total Columns     : {len(df.columns)}")
        print(f"  Missing Values    : {df.isnull().sum().sum()}")
        print(f"  Duplicate Rows    : {df.duplicated().sum()}")

        print(f"\n  Budget_Status Distribution:")
        for k, v in df["Budget_Status"].value_counts().items():
            pct = v / len(df) * 100
            bar = "█" * int(pct / 2)
            print(f"     {k:<20}: {v:,}  ({pct:.1f}%)  {bar}")

        if df["Budget_Status"].nunique() < 2:
            print("\n  ⚠️  WARNING : Only ONE class in Budget_Status!")
        else:
            print("\n  ✅ Both Budget_Status classes present!")

    # ─────────────────────────────────────────
    # Save Dataset
    # ─────────────────────────────────────────
    def save_dataset(self, df):

        csv_file   = DATASET_DIR / "house_renovation_dataset_20000.csv"
        excel_file = DATASET_DIR / "house_renovation_dataset_20000.xlsx"

        df.to_csv(csv_file, index=False)
        print("\n" + "=" * 55)
        print("   FILES SAVED")
        print("=" * 55)
        print(f"\n  ✅ CSV saved   → {csv_file}")

        try:
            df.to_excel(excel_file, index=False)
            print(f"  ✅ Excel saved → {excel_file}")
        except Exception as e:
            print(f"  ⚠️  Excel save skipped : {e}")

        print(f"\n  ✅ Total Rows  : {len(df):,}")
        print(f"  ✅ Total Cols  : {len(df.columns)}")


if __name__ == "__main__":

    gen     = HouseRenovationDatasetGenerator()
    dataset = gen.generate_dataset(20000)

    gen.validate_dataset(dataset)
    gen.save_dataset(dataset)

    print("\n" + "=" * 55)
    print("  Sample — First 3 Rows")
    print("=" * 55)
    print(dataset.head(3).to_string())
    print("=" * 55)