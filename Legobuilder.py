
import requests
import streamlit as st

# =========================
# API KEYS (STREAMLIT)
# =========================
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
REBRICKABLE_API_KEY = st.secrets["REBRICKABLE_API_KEY"]

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

# =========================
# HELPER: FIX SET FORMAT
# =========================
def normalize_set_number(set_number):
    if "-" not in set_number:
        return set_number + "-1"
    return set_number

# =========================
# BUILD INVENTORY
# =========================
def build_inventory(set_number):
    url = f"https://rebrickable.com/api/v3/lego/sets/{set_number}/parts/"
    headers = {"Authorization": f"key {REBRICKABLE_API_KEY}"}

    inventory = {
        "total_parts": 0,
        "by_category": {},
        "by_color": {},
        "parts": {}
    }

    while url:
        r = requests.get(url, headers=headers)

        if r.status_code != 200:
            print("❌ Failed to fetch parts")
            return None

        data = r.json()

        for item in data["results"]:
            qty = item["quantity"]
            part_name = item["part"]["name"]
            color_name = item["color"]["name"]

            part_key = f"{part_name} ({color_name})"

            inventory["total_parts"] += qty

            # Store real parts
            inventory["parts"][part_key] = inventory["parts"].get(part_key, 0) + qty

            # Keep old stats
            cat = item["part"].get("part_cat", {}).get("name", "Unknown")
            inventory["by_category"][cat] = inventory["by_category"].get(cat, 0) + qty
            inventory["by_color"][color_name] = inventory["by_color"].get(color_name, 0) + qty

        url = data["next"]

    return inventory



# =========================
# EXTRACT CONSTRAINTS
# =========================
def extract_constraints(inventory):
    return {
        "total_parts": inventory.get("total_parts", 0),
        "categories": inventory.get("by_category", {}),
        "colors": inventory.get("by_color", {}),
        "special_parts": inventory.get("special_parts", [])
    }

# =========================
# SCORING SYSTEM
# =========================
def score_builds(inventory):
    scores = {
        "vehicle": 0,
        "robot": 0,
        "structure": 0
    }

    total = inventory["total_parts"]
    colors = inventory["by_color"]

    scores["structure"] += total // 50
    scores["structure"] += len(colors)
    scores["vehicle"] += len(colors) // 2
    scores["robot"] += len(colors) // 2

    for color in colors:
        if "Black" in color or "Gray" in color:
            scores["vehicle"] += 2
        if "Red" in color or "Blue" in color:
            scores["robot"] += 2

    return scores

def choose_best_build(scores):
    return max(scores, key=scores.get)

# =========================
# AI BUILD DESIGN
# =========================
def generate_build_description(build_type, selected_parts, size):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    part_list = "\n".join(
        [f"- {part} x{qty}" for part, qty in selected_parts.items()]
    )

    prompt = f"""
You are a professional LEGO instruction designer.

AVAILABLE PARTS (YOU MAY ONLY USE THESE):

{part_list}

RULES:
- Use ONLY the parts listed above
- Do NOT invent new parts
- Do NOT change colors
- Do NOT exceed the quantities
- The build must match this theme: {build_type}
- Build size: {size.upper()}

PART NAMING RULE:
You MUST use the exact part names as written in the AVAILABLE PARTS list.
Do NOT reword, resize, rename, or generalize parts.
Example:
If the list says "Slope 30 1x2 (Dark Bluish Gray)",
you must write exactly:
"Slope 30 1x2 (Dark Bluish Gray)"


TARGET PART USAGE:
SMALL: ~30–200 parts  
MEDIUM: ~250–400 parts  
LARGE: ~500–800+ parts  

If the set does not support this size, explain why and suggest a better build type.

Your job:
Create a realistic LEGO build using ONLY these parts.
Explain how to build it step-by-step.

FORMAT:
- Title
- Sections (Base, Body, Details, etc.)
- Each section:
  - Parts Required
  - Instructions

Start now.
"""

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4
    }

    r = requests.post(OPENAI_CHAT_URL, headers=headers, json=payload, timeout=60)

    if r.status_code != 200:
        print("❌ Build description generation failed:", r.text)
        return None

    return r.json()["choices"][0]["message"]["content"]


# =========================
# AI GUIDANCE
# =========================
def generate_ai_guidance(build_description, inventory, constraints):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    color_list = ", ".join(inventory["by_color"].keys())
    total_parts = inventory["total_parts"]


    prompt = f"""
You are a LEGO building assistant.

Based on the build design below, provide:

- Estimated build time  
- Difficulty level  
- Stability tips  

Do NOT change the build.  
Do NOT add instructions.  
Do NOT suggest new parts.

Build Design:
{build_description}

"""

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6
    }

    try:
        r = requests.post(OPENAI_CHAT_URL, headers=headers, json=payload, timeout=60)

        if r.status_code != 200:
            print("❌ AI guidance failed:", r.text)
            return None

        text = r.json()["choices"][0]["message"]["content"]
        return text.split("\n")

    except Exception as e:
        print("❌ AI guidance error:", e)
        return None
    
def recommend_build_types(inventory):
    categories = inventory.get("by_category", {})

    bricks = categories.get("Bricks", 0)
    plates = categories.get("Plates", 0)
    slopes = categories.get("Slopes", 0)
    technic = categories.get("Technic", 0)
    minifig = categories.get("Minifig Parts", 0)

    recommendations = []

    if bricks + plates > 150:
        recommendations.append("structure")

    if slopes > 50 or technic > 40:
        recommendations.append("vehicle")

    if minifig > 10:
        recommendations.append("creature")

    if not recommendations:
        recommendations.append("small prop / decoration")

    return recommendations

def select_build_parts(inventory, size):
    total_parts = inventory["total_parts"]

    if size == "small":
        target = min(120, total_parts)

    elif size == "medium":
        if total_parts < 200:
            return {}
        target = min(350, total_parts)

    else:  # large
        if total_parts < 500:
            return {}
        target = min(700, total_parts)

    selected = {}
    count = 0

    for part, qty in inventory["parts"].items():
        for _ in range(qty):
            if count >= target:
                return selected
            selected[part] = selected.get(part, 0) + 1
            count += 1

    return selected


# =========================
# MAIN LOOP
# =========================
def run_cli():

    while True:

        print("\n🧱 LEGO Builder")
        set_number = input("Enter LEGO set number (or type quit): ").strip()

        if set_number.lower() == "quit":
            print("\n👋 Goodbye!")
            break

        set_number = normalize_set_number(set_number)
        inventory = build_inventory(set_number)

        if not inventory:
            print("❌ Could not load set data.")
            continue

        print("\n📦 SET PART SUMMARY:")
        print("Total parts:", inventory["total_parts"])

        print("\n🔧 Sample real parts:")
        for i, (part, qty) in enumerate(inventory["parts"].items()):
            print(f"- {part}: {qty}")
            if i == 9:
                break

        recommended = recommend_build_types(inventory)

        print("\n🧠 This set is best suited for:")
        for r in recommended:
            print("- ", r)

        total = inventory["total_parts"]

        # ===== BUILD SIZE SELECTION =====
        print("\n📏 Choose build size:")

        if total >= 500:
            print("Options: SMALL, MEDIUM, or LARGE")
            size = input("Choose size (small / medium / large): ").strip().lower()
            if size not in ["small", "medium", "large"]:
                size = "medium"

        elif total >= 200:
            print("Options: SMALL or MEDIUM")
            size = input("Choose size (small / medium): ").strip().lower()
            if size not in ["small", "medium"]:
                size = "small"

        else:
            print("Only SMALL builds available (set is too small for medium or large).")
            size = "small"

        # ===== SIZE VALIDATION =====
        if size == "large" and total < 500:
            print("\n⚠️ This set is too small for a LARGE build.")
            print("Switching to SMALL build instead.")
            size = "small"

        if size == "medium" and total < 200:
            print("\n⚠️ This set is too small for a MEDIUM build.")
            print("Switching to SMALL build instead.")
            size = "small"

        print("DEBUG size selected:", size)

        # ===== PART SELECTION =====
        selected_parts = select_build_parts(inventory, size)

        print("\n🧱 Selected build parts:")
        for part, qty in selected_parts.items():
            print(f"- {part}: {qty}")

        # ===== BUILD TYPE SELECTION =====
        scores = score_builds(inventory)

        print("\n📊 Build capability scores:")
        for k, v in scores.items():
            print(f"- {k}: {v}")

        choice = input(
            "\nChoose build type:\n"
            "- vehicle (car, bike, spaceship, tank)\n"
            "- robot (mech, droid, creature)\n"
            "- structure (house, tower, café, base)\n"
            "You can also type a custom theme.\n"
            "Or press Enter to choose best: "
        ).strip().lower()

        if choice:
            build_type = choice
        else:
            build_type = choose_best_build(scores)

        print("DEBUG build type:", build_type)

        # ===== AI BUILD =====
        print("\n🏗️ Generating build design...")
        build_description = generate_build_description(build_type, selected_parts, size)

        print("\n🏗️ BUILD DESIGN:\n", build_description)

        print("\n🤖 Generating AI build guidance...")
        guidance = generate_ai_guidance(build_description, inventory, extract_constraints(inventory))

        if not guidance:
            print("⚠️ AI guidance failed.")
        else:
            print("\n📘 AI BUILD GUIDANCE:")
            for g in guidance:
                print("- ", g)

        # ===== NOTES =====
        print("\nℹ️ Note:")
        print("This build is a conceptual guide based on available parts.")
        print("Some connections may require creative adjustment, as the AI cannot fully simulate LEGO physics.")
        print("Use your own building experience to refine stability and connections.")
        print("This is a compact build concept. You can expand it using extra parts from your set.")

        print("\n🔎 Want to see how the parts look?")
        print("Go to BrickLink and search your set number to see clear images of every piece and color.")


if __name__ == "__main__":
    run_cli()
