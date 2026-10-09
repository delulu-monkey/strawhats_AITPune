import pandas as pd

# (display name, INDB food_code), chosen by hand from the search output
DISHES = [
    ("Idli (1 piece)", "ASC144"), ("Plain dosa", "BFP148"), ("Masala dosa", "ASC146"),
    ("Poha (bowl)", "BFP044"), ("Semolina upma (bowl)", "BFP039"),
    ("Plain paratha", "ASC097"), ("Aloo paratha", "ASC098"), ("Chapati / roti", "ASC096"),
    ("Boiled rice (plate)", "ASC113"), ("Moong dal (bowl)", "ASC151"),
    ("Rajma curry (bowl)", "ASC165"), ("Sambar (bowl)", "ASC167"),
    ("Khichdi (small bowl)", "BFP144"), ("Curd rice (plate)", "ASC126"),
    ("Vegetable biryani (plate)", "ASC123"), ("Mutton biryani (plate)", "ASC122"),
    ("Plain pulao (plate)", "ASC114"),
]

t = pd.read_excel("data/raw/indb/INDB.xlsx")
codes = [c for _, c in DISHES]
missing = set(codes) - set(t.food_code)
assert not missing, f"codes not found: {missing}"

sel = t.set_index("food_code").loc[codes]
out = pd.DataFrame({
    "dish": [n for n, _ in DISHES],
    "indb_name": sel.food_name.values,
    "indb_code": codes,
    "serving": sel.servings_unit.values,
    "kcal": sel.unit_serving_energy_kcal.round(0).values,
    "carbs": sel.unit_serving_carb_g.round(1).values,
    "protein": sel.unit_serving_protein_g.round(1).values,
    "fat": sel.unit_serving_fat_g.round(1).values,
    "fiber": sel.unit_serving_fibre_g.round(1).values,
})

# Plausibility check: flag anything that looks like the frying-oil problem
bad = out[(out.fat > 60) | (out.kcal > 700) | out.isna().any(axis=1)]
print(out.to_string(index=False))
print("\nFlagged as implausible:", bad.dish.tolist() or "none")

out.to_csv("data/indian_meals.csv", index=False)
print("Saved data/indian_meals.csv")
