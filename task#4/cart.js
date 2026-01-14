const CART_KEY = 'shopping_cart';

let cart = [];
let allProducts = [];

function loadCart() {
    const savedCart = localStorage.getItem(CART_KEY);
    if (savedCart) {
        cart = JSON.parse(savedCart);
    }
    updateCartDisplay();
}

function saveCart() {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
}

async function loadProducts() {
    const productsDiv = document.getElementById('products-list');
    productsDiv.innerHTML = '<p>Loading products...</p>';

    try {
        const response = await fetch('https://dummyjson.com/products?limit=20');
        
        if (!response.ok) {
            throw new Error('Could not load products');
        }
        
        const data = await response.json();
        allProducts = data.products;
        displayProducts(allProducts);
    } catch (error) {
        console.error('Oops, could not load products:', error);
        productsDiv.innerHTML = '<p style="color: red;">Could not load products. Please check your internet and try again.</p>';
    }
}

function displayProducts(products) {
    const productsDiv = document.getElementById('products-list');
    productsDiv.innerHTML = '';

    if (!products || products.length === 0) {
        productsDiv.innerHTML = '<p>No products available right now.</p>';
        return;
    }

    for (let i = 0; i < products.length; i++) {
        const product = products[i];
        
        const productBox = document.createElement('div');
        productBox.style.border = '1px solid #ccc';
        productBox.style.padding = '10px';
        productBox.style.marginBottom = '10px';
        productBox.style.backgroundColor = '#fff';
        
        const productName = document.createElement('h3');
        productName.textContent = product.title;
        productBox.appendChild(productName);
        
        if (product.brand) {
            const brandText = document.createElement('p');
            brandText.innerHTML = `<strong>Brand:</strong> ${product.brand}`;
            productBox.appendChild(brandText);
        }
        
        const priceText = document.createElement('p');
        priceText.innerHTML = `<strong>Price:</strong> $${product.price}`;
        productBox.appendChild(priceText);
        
        const categoryText = document.createElement('p');
        categoryText.innerHTML = `<strong>Category:</strong> ${product.category}`;
        productBox.appendChild(categoryText);
        
        const addButton = document.createElement('button');
        addButton.textContent = 'Add to Cart';
        addButton.onclick = function() {
            addToCart(product.id, product.title, product.price);
        };
        productBox.appendChild(addButton);
        
        productsDiv.appendChild(productBox);
    }
}

function addToCart(id, name, price) {
    let foundItem = null;
    for (let i = 0; i < cart.length; i++) {
        if (cart[i].id === id) {
            foundItem = cart[i];
            break;
        }
    }
    
    if (foundItem) {
        foundItem.quantity = foundItem.quantity + 1;
    } else {
        cart.push({
            id: id,
            name: name,
            price: price,
            quantity: 1
        });
    }
    
    saveCart();
    updateCartDisplay();
    alert('Added to cart!');
}

function removeFromCart(id) {
    const newCart = [];
    for (let i = 0; i < cart.length; i++) {
        if (cart[i].id !== id) {
            newCart.push(cart[i]);
        }
    }
    cart = newCart;
    
    saveCart();
    updateCartDisplay();
}

function updateQuantity(id, newQuantity) {
    let foundItem = null;
    for (let i = 0; i < cart.length; i++) {
        if (cart[i].id === id) {
            foundItem = cart[i];
            break;
        }
    }
    
    if (foundItem) {
        const quantity = parseInt(newQuantity);
        
        if (isNaN(quantity) || quantity <= 0) {
            removeFromCart(id);
        } else {
            foundItem.quantity = quantity;
            saveCart();
            updateCartDisplay();
        }
    }
}

function clearCart() {
    const userSure = confirm('Are you sure you want to empty your cart?');
    if (userSure) {
        cart = [];
        saveCart();
        updateCartDisplay();
    }
}

function updateCartDisplay() {
    const cartDiv = document.getElementById('cart-items');
    const cartCount = document.getElementById('cart-count');
    const cartTotal = document.getElementById('cart-total');
    
    if (cart.length === 0) {
        cartDiv.innerHTML = '<p>Your cart is empty.</p>';
        cartCount.textContent = '0';
        cartTotal.textContent = '0.00';
        return;
    }
    
    cartDiv.innerHTML = '';
    
    let totalPrice = 0;
    let totalItems = 0;
    
    for (let i = 0; i < cart.length; i++) {
        const item = cart[i];
        
        const itemBox = document.createElement('div');
        itemBox.style.border = '1px solid #ddd';
        itemBox.style.padding = '10px';
        itemBox.style.marginBottom = '10px';
        itemBox.style.backgroundColor = '#f9f9f9';
        
        const itemTotal = item.price * item.quantity;
        totalPrice = totalPrice + itemTotal;
        totalItems = totalItems + item.quantity;
        
        const itemName = document.createElement('h4');
        itemName.textContent = item.name;
        itemBox.appendChild(itemName);
        
        const itemPrice = document.createElement('p');
        itemPrice.innerHTML = `<strong>Price:</strong> $${item.price.toFixed(2)}`;
        itemBox.appendChild(itemPrice);
        
        const quantityLine = document.createElement('p');
        quantityLine.innerHTML = '<strong>Quantity:</strong> ';
        
        const quantityInput = document.createElement('input');
        quantityInput.type = 'number';
        quantityInput.value = item.quantity;
        quantityInput.min = '1';
        quantityInput.style.width = '60px';
        quantityInput.onchange = function() {
            updateQuantity(item.id, this.value);
        };
        quantityLine.appendChild(quantityInput);
        itemBox.appendChild(quantityLine);
        
        const subtotalLine = document.createElement('p');
        subtotalLine.innerHTML = `<strong>Subtotal:</strong> $${itemTotal.toFixed(2)}`;
        itemBox.appendChild(subtotalLine);
        
        const removeButton = document.createElement('button');
        removeButton.textContent = 'Remove';
        removeButton.onclick = function() {
            removeFromCart(item.id);
        };
        itemBox.appendChild(removeButton);
        
        cartDiv.appendChild(itemBox);
    }
    
    cartCount.textContent = totalItems;
    cartTotal.textContent = totalPrice.toFixed(2);
}

document.addEventListener('DOMContentLoaded', function() {
    loadCart();
    loadProducts();
    
    const clearButton = document.getElementById('clear-cart-btn');
    clearButton.addEventListener('click', clearCart);
});