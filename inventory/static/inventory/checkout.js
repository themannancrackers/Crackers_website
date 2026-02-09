document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token from window variable (set in base.html)
    
    // Minimum order amount constant
    const MIN_ORDER_AMOUNT = 3000;

    // Get checkout elements
    const checkoutForm = document.getElementById('checkoutForm');
    const checkoutButton = document.getElementById('proceedToCheckout');

    // Handle checkout process
    checkoutButton?.addEventListener('click', async function() {
        if (!checkoutForm.checkValidity()) {
            checkoutForm.classList.add('was-validated');
            return;
        }

        if (!window.cart || window.cart.length === 0) {
            showToast('Your cart is empty!', 'warning');
            return;
        }
        
        // Validate minimum order amount
        const cartTotal = window.cart.reduce((total, item) => total + (item.price * item.quantity), 0);
        if (cartTotal < MIN_ORDER_AMOUNT) {
            showToast(`Minimum order amount is ₹${MIN_ORDER_AMOUNT}. Current total: ₹${cartTotal.toFixed(2)}`, 'warning');
            return;
        }

        const customerData = {
            fullName: document.getElementById('fullName').value,
            email: document.getElementById('email').value,
            phone: document.getElementById('phone').value,
            deliveryAddress: document.getElementById('deliveryAddress').value,
            updateProfile: document.getElementById('updateProfile')?.checked || false
        };

        try {
            const response = await fetch('/inventory/checkout/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken
                },
                body: JSON.stringify({
                    customerData: customerData,
                    cartItems: window.cart.reduce((obj, item) => {
                        obj[item.id] = {
                            name: item.name,
                            quantity: item.quantity,
                            price: item.price
                        };
                        return obj;
                    }, {})
                }),
                credentials: 'same-origin' // Include cookies in request
            });

            const data = await response.json();

            if (data.success) {
                // Show success message
                showDiwaliSuccess(data.orderSummary.total);
                
                // Clear cart
                cartItems = {};
                updateCartTotal();
                updateCartCount();
                renderCartItems();

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('cartModal'));
                modal?.hide();
            } else {
                showToast(data.error || 'Failed to place order. Please try again.', 'danger');
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Network error. Please try again.', 'danger');
        }
    });
});