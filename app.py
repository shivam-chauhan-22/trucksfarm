from flask import Flask, render_template, request
import pandas as pd
from urllib.parse import quote, unquote
from flask_frozen import Freezer

app = Flask(__name__)

# Use relative path for CSV
CSV_PATH = "TATACSVFILE2.csv"
df = pd.read_csv(CSV_PATH)
df.columns = df.columns.str.strip()

brand_col = 'name'
model_col = 'modelName'
variant_col = 'slug'
fuel_col = 'fuel-type'
gvw_col = 'gross-vehicle-weight-kg'
mileage_col = 'mileage'
power_col = 'power-hp'
image_col = 'image-url'

df['popular'] = False
df.loc[:4, 'popular'] = True

# Routes
@app.route('/')
def home():
    search = request.args.get('search', '').lower()
    brand_filter = request.args.get('brand', '')
    fuel_filter = request.args.get('fuel', '')
    sort_order = request.args.get('sort', 'asc')
    page = int(request.args.get('page', 1))
    per_page = 12

    models_grouped = df.groupby(model_col)
    model_cards = []
    for model_name, group in models_grouped:
        first_row = group.iloc[0]
        card = {
            'brand': first_row[brand_col],
            'model': model_name,
            'model_url': quote(model_name.lower()),
            'gvw': first_row.get(gvw_col, ''),
            'fuel': first_row.get(fuel_col, ''),
            'mileage': first_row.get(mileage_col, ''),
            'power': first_row.get(power_col, ''),
            'image': first_row.get(image_col, None),
            'popular': first_row.get('popular', False),
            'variants': group.to_dict(orient='records')
        }
        model_cards.append(card)

    if search:
        model_cards = [m for m in model_cards if search in m['model'].lower()]
    if brand_filter:
        model_cards = [m for m in model_cards if m['brand'].lower() == brand_filter.lower()]
    if fuel_filter:
        model_cards = [m for m in model_cards if fuel_filter.lower() in str(m['fuel']).lower()]

    model_cards.sort(key=lambda x: x['model'].lower(), reverse=(sort_order == 'desc'))

    total = len(model_cards)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    end = min(start + per_page, total)
    model_cards_paginated = model_cards[start:end]

    brands = sorted(df[brand_col].dropna().unique())
    fuels = sorted(df[fuel_col].dropna().unique())

    return render_template('index.html', model_cards=model_cards_paginated,
                          page=page, total_pages=total_pages, search=search,
                          brands=brands, fuels=fuels, selected_brand=brand_filter,
                          selected_fuel=fuel_filter, sort_order=sort_order)

@app.route('/brands')
def brands_page():
    brands = sorted(df[brand_col].dropna().unique())
    return render_template('brands.html', brands=brands)

@app.route('/model/<model>')
def model_detail(model):
    model = unquote(model)
    variants = df[df[model_col].str.lower() == model.lower()].to_dict(orient='records')
    if not variants:
        return "Model not found", 404
    return render_template('model_detail.html', model_name=model, variants=variants,
                          brand_col=brand_col, variant_col=variant_col,
                          gvw_col=gvw_col, fuel_col=fuel_col,
                          mileage_col=mileage_col, power_col=power_col)

@app.route('/variant/<variant_slug>')
def variant_detail(variant_slug):
    variant_slug = unquote(variant_slug)
    variant = df[df[variant_col].str.lower() == variant_slug.lower()].to_dict(orient='records')
    if not variant:
        return "Variant not found", 404
    variant = variant[0]
    return render_template('variant_detail.html', variant=variant, brand_col=brand_col,
                          model_col=model_col, variant_col=variant_col)

# Frozen-Flask setup
freezer = Freezer(app)

@freezer.register_generator
def model_generator():
    models = df['modelName'].dropna().unique()
    for model in models:
        yield {'model': model.lower().replace(' ', '-')}

@freezer.register_generator
def variant_generator():
    variants = df['slug'].dropna().unique()
    for variant in variants:
        yield {'variant_slug': variant.lower()}

@freezer.register_generator
def paginated_home():
    total = len(df.groupby(model_col))
    total_pages = max(1, (total + 11) // 12)
    for page in range(1, total_pages + 1):
        yield {'page': page}
    brands = df[brand_col].dropna().unique()[:5]
    for brand in brands:
        yield {'brand': brand.lower(), 'page': 1}
    fuels = df[fuel_col].dropna().unique()[:5]
    for fuel in fuels:
        yield {'fuel': fuel.lower(), 'page': 1}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)