from flask import render_template
from . import product

# Assuming products module is in the src directory
from app.data.products import products

@product.route('/product/<int:id>')
def product_detail(id):
    # Find the product with the given id
    product_item = next((product for product in products if product['id'] == id), None)
    if product_item is None:
        # return a 404 page if the product is not found
        return render_template('404.html'), 404
    else:
        return render_template('product/product_detail.html', product=product_item)
