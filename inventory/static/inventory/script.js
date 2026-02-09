document.addEventListener('DOMContentLoaded', function() {
    const productGrid = document.getElementById('product-grid');
    const cartTotalElements = document.querySelectorAll('#cart-total');
    const cartItemsCount = document.querySelector('.cart-items-count');
    const cartItemsContainer = document.getElementById('cartItems');
    const modalSubtotal = document.getElementById('modalSubtotal');
    const checkoutForm = document.getElementById('checkoutForm');
    const checkoutButton = document.getElementById('proceedToCheckout');
    let totalCartAmount = 0;
    let cartItems = {};
    
    // Minimum order amount constant
    const MIN_ORDER_AMOUNT = 3000;

    /* -------------------- 🧮 CORE CART UTILITIES -------------------- */
    function updateAllCartTotals(amount) {
        cartTotalElements.forEach(element => {
            element.textContent = amount.toFixed(2);
        });
        modalSubtotal.textContent = amount.toFixed(2);
        
        // Update checkout button state based on minimum amount
        updateCheckoutButtonState(amount);
    }
    
    function updateCheckoutButtonState(amount) {
        if (checkoutButton) {
            if (amount < MIN_ORDER_AMOUNT) {
                checkoutButton.disabled = true;
                checkoutButton.title = `Minimum order amount is ₹${MIN_ORDER_AMOUNT}`;
                checkoutButton.style.opacity = '0.6';
                checkoutButton.style.cursor = 'not-allowed';
            } else {
                checkoutButton.disabled = false;
                checkoutButton.title = 'Proceed to Checkout';
                checkoutButton.style.opacity = '1';
                checkoutButton.style.cursor = 'pointer';
            }
        }
    }

    function updateCartCount() {
        const itemCount = Object.values(cartItems).reduce((sum, item) => sum + item.quantity, 0);
        cartItemsCount.textContent = `(${itemCount} items)`;
    }

    function renderCartItems() {
        cartItemsContainer.innerHTML = '';
        Object.entries(cartItems).forEach(([id, item]) => {
            const itemTotal = item.price * item.quantity;
            const itemHtml = `
                <div class="cart-item" data-id="${id}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="mb-1">${item.name}</h5>
                            <p class="mb-0">Quantity: ${item.quantity}</p>
                        </div>
                        <div class="text-end">
                            <div class="cart-item-price fw-bold text-primary">₹${itemTotal.toFixed(2)}</div>
                            <button class="btn btn-sm btn-danger remove-item mt-2">
                                <i class="bi bi-trash"></i> Remove
                            </button>
                        </div>
                    </div>
                </div>
            `;
            cartItemsContainer.insertAdjacentHTML('beforeend', itemHtml);
        });
    }

    function updateItemTotal(card) {
        const quantity = parseInt(card.querySelector('.quantity-input').value);
        const price = parseFloat(card.querySelector('.price').innerText.replace('₹', ''));
        const totalPrice = (quantity * price).toFixed(2);
        const totalElement = card.querySelector('.total-price');
        if (totalElement) totalElement.innerText = totalPrice;
        updateCartTotal();
    }

    function updateCartTotal() {
        totalCartAmount = Object.values(cartItems).reduce((sum, item) => sum + (item.price * item.quantity), 0);
        updateAllCartTotals(totalCartAmount);
    }

    /* -------------------- 🔢 QUANTITY CONTROLS -------------------- */
    productGrid.addEventListener('click', function(e) {
        if (e.target.classList.contains('decrease-qty') || e.target.classList.contains('increase-qty')) {
            const card = e.target.closest('.product-card');
            const input = card.querySelector('.quantity-input');
            const currentValue = parseInt(input.value);
            const maxStock = parseInt(input.max);

            if (e.target.classList.contains('decrease-qty')) {
                if (currentValue > 1) input.value = currentValue - 1;
            } else {
                if (currentValue < maxStock) input.value = currentValue + 1;
            }

            updateItemTotal(card);
        }
    });

    productGrid.addEventListener('input', function(e) {
        if (e.target.classList.contains('quantity-input')) {
            const card = e.target.closest('.product-card');
            const maxStock = parseInt(e.target.max);
            let value = parseInt(e.target.value) || 1;
            value = Math.max(1, Math.min(value, maxStock));
            e.target.value = value;
            updateItemTotal(card);
        }
    });

    /* -------------------- 🛒 ADD TO CART LOGIC -------------------- */
    productGrid.addEventListener('click', async function(e) {
        if (e.target.classList.contains('add-to-cart') || e.target.parentElement.classList.contains('add-to-cart')) {
            const card = e.target.closest('.product-card');
            const productId = card.dataset.productId;
            const quantity = parseInt(card.querySelector('.quantity-input').value);
            const stockElement = card.querySelector('.stock-quantity');
            const productName = card.querySelector('.card-title').textContent;
            const currentStock = parseInt(stockElement.innerText);

            try {
                const response = await fetch('/inventory/update-stock/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ product_id: productId, quantity })
                });

                const data = await response.json();
                if (data.success) {
                    stockElement.innerText = data.new_stock;
                    const quantityInput = card.querySelector('.quantity-input');
                    quantityInput.max = data.new_stock;

                    if (data.new_stock === 0) {
                        quantityInput.disabled = true;
                        e.target.disabled = true;
                    }

                    if (data.is_low_stock) card.classList.add('low-stock');

                    if (!cartItems[productId]) {
                        cartItems[productId] = {
                            name: productName,
                            quantity: 0,
                            price: parseFloat(card.querySelector('.price').innerText.replace('₹', ''))
                        };
                    }

                    cartItems[productId].quantity += quantity;
                    updateCartTotal();
                    updateCartCount();
                    renderCartItems();

                    // Show feedback about minimum order
                    if (totalCartAmount < MIN_ORDER_AMOUNT) {
                        const remaining = (MIN_ORDER_AMOUNT - totalCartAmount).toFixed(2);
                        const message = `🎇 Added ${quantity} × ${productName} to cart. Add ₹${remaining} more to reach minimum order amount`;
                        showToast(message, 'info');
                    } else {
                        const message = `🎇 Added ${quantity} × ${productName} to cart`;
                        showToast(message, 'success');
                    }
                } else {
                    showToast(data.error || 'Failed to add items to cart', 'danger');
                }
            } catch (error) {
                console.error('Error:', error);
                showToast('Failed to update cart. Please try again.', 'danger');
            }
        }
    });

    /* -------------------- ❌ REMOVE CART ITEM -------------------- */
    cartItemsContainer.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-item') || e.target.closest('.remove-item')) {
            const cartItem = e.target.closest('.cart-item');
            const itemId = cartItem.dataset.id;
            delete cartItems[itemId];
            updateCartTotal();
            updateCartCount();
            renderCartItems();
            showToast('Item removed from cart', 'warning');
        }
    });

    /* -------------------- 🎇 TOAST UTILITY -------------------- */
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-bg-${type} border-0 show position-fixed bottom-0 end-0 m-3`;
        toast.style.zIndex = '3000';
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body fw-semibold">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    /* -------------------- 🧭 TOUCH DRAG SUPPORT FOR CAROUSEL -------------------- */
    let isDragging = false;
    let startX, scrollLeft;

    productGrid.addEventListener('mousedown', (e) => {
        if (window.innerWidth > 768) return;
        isDragging = true;
        startX = e.pageX - productGrid.offsetLeft;
        scrollLeft = productGrid.scrollLeft;
        productGrid.classList.add('dragging');
    });

    productGrid.addEventListener('mouseleave', () => { isDragging = false; });
    productGrid.addEventListener('mouseup', () => { isDragging = false; productGrid.classList.remove('dragging'); });

    productGrid.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        e.preventDefault();
        const x = e.pageX - productGrid.offsetLeft;
        const walk = (x - startX) * 1.2;
        productGrid.scrollLeft = scrollLeft - walk;
    });

    /* -------------------- 🔄 INITIALIZATION -------------------- */
    document.querySelectorAll('.product-card').forEach(updateItemTotal);
});
