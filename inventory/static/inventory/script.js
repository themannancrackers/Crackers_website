document.addEventListener("DOMContentLoaded", function () {
  const productGrid = document.getElementById("product-grid");
  const cartTotalElements = document.querySelectorAll("#cart-total");
  const cartItemsCount = document.querySelector(".cart-items-count");
  const cartItemsContainer = document.getElementById("cartItems");
  const modalSubtotal = document.getElementById("modalSubtotal");
  const checkoutForm = document.getElementById("checkoutForm");
  const checkoutButton = document.getElementById("proceedToCheckout");
  let totalCartAmount = 0;
  let cartItems = {};

  // Minimum order amount constant
  const MIN_ORDER_AMOUNT = 2500;

  // Maintain window.cart for checkout.js compatibility
  window.cart = [];

  /* -------------------- 🧮 CORE CART UTILITIES -------------------- */
  function updateAllCartTotals(amount) {
    cartTotalElements.forEach((element) => {
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
        checkoutButton.style.opacity = "0.6";
        checkoutButton.style.cursor = "not-allowed";
      } else {
        checkoutButton.disabled = false;
        checkoutButton.title = "Proceed to Checkout";
        checkoutButton.style.opacity = "1";
        checkoutButton.style.cursor = "pointer";
      }
    }
  }

  function updateCartCount() {
    const itemCount = Object.values(cartItems).reduce(
      (sum, item) => sum + item.quantity,
      0,
    );
    cartItemsCount.textContent = `(${itemCount} items)`;
  }

  function renderCartItems() {
    cartItemsContainer.innerHTML = "";
    Object.entries(cartItems).forEach(([id, item]) => {
      const itemTotal = item.price * item.quantity;
      // Calculate a simulated MRP and discount for display (20% markup as MRP)
      const simulatedMrp = (item.price * 1.2).toFixed(2);
      const discount = (simulatedMrp - item.price).toFixed(2);
      
      const itemHtml = `
                <div class="cart-item modern-cart-item" data-id="${id}">
                    <div class="cart-item-container">
                        <!-- Product Image -->
                        <div class="cart-item-image">
                            <i class="fa-solid fa-box" style="font-size: 2.5rem; color: #0d6efd;"></i>
                        </div>
                        
                        <!-- Product Details -->
                        <div class="cart-item-details">
                            <h5 class="cart-item-title">${item.name}</h5>
                            
                            <!-- Pricing Info -->
                            <div class="pricing-section">
                                <div class="pricing-row">
                                    <span class="pricing-label">MRP:</span>
                                    <span class="pricing-value mrp-value" style="color: #dc3545;">₹${simulatedMrp}</span>
                                    <span class="pricing-label" style="margin-left: 15px;">Discount:</span>
                                    <span class="pricing-value discount-value">₹${discount}</span>
                                </div>
                                <div class="pricing-row">
                                    <span class="pricing-label">Amount:</span>
                                    <span class="pricing-value amount-value" style="color: #28a745; font-weight: 600;">₹${item.price.toFixed(2)}</span>
                                    <span class="pricing-label" style="margin-left: 15px;">Unit Price:</span>
                                    <span class="pricing-value unit-price">₹${item.price.toFixed(2)}</span>
                                </div>
                            </div>
                            
                            <!-- Quantity Controls -->
                            <div class="quantity-control-section">
                                <span class="quantity-label">Qty:</span>
                                <button class="qty-btn decrease-cart-qty" data-id="${id}" style="background: #dc3545;">
                                    <i class="fa-solid fa-minus"></i>
                                </button>
                                <input type="number" class="qty-input cart-qty-input" value="${item.quantity}" min="1" data-id="${id}" readonly>
                                <button class="qty-btn increase-cart-qty" data-id="${id}" style="background: #28a745;">
                                    <i class="fa-solid fa-plus"></i>
                                </button>
                                <span class="total-amount-badge">₹${itemTotal.toFixed(2)}</span>
                            </div>
                        </div>
                        
                        <!-- Remove Button -->
                        <div class="cart-item-actions">
                            <button class="btn-remove-item remove-item" data-id="${id}" title="Remove item">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
      cartItemsContainer.insertAdjacentHTML("beforeend", itemHtml);
    });
    
    // Add event listeners for quantity controls
    attachCartQuantityListeners();
  }
  
  function attachCartQuantityListeners() {
    // Decrease quantity
    document.querySelectorAll(".decrease-cart-qty").forEach(btn => {
      btn.addEventListener("click", function(e) {
        e.preventDefault();
        const id = this.dataset.id;
        if (cartItems[id] && cartItems[id].quantity > 1) {
          cartItems[id].quantity--;
          updateCartTotal();
          updateCartCount();
          renderCartItems();
        }
      });
    });
    
    // Increase quantity
    document.querySelectorAll(".increase-cart-qty").forEach(btn => {
      btn.addEventListener("click", function(e) {
        e.preventDefault();
        const id = this.dataset.id;
        if (cartItems[id]) {
          cartItems[id].quantity++;
          updateCartTotal();
          updateCartCount();
          renderCartItems();
        }
      });
    });
  }

  function updateItemTotal(card) {
    const quantity = parseInt(card.querySelector(".quantity-input").value);
    const price = parseFloat(
      card.querySelector(".price").innerText.replace("₹", ""),
    );
    const totalPrice = (quantity * price).toFixed(2);
    const totalElement = card.querySelector(".total-price");
    if (totalElement) totalElement.innerText = totalPrice;
    updateCartTotal();
  }

  function updateCartTotal() {
    totalCartAmount = Object.values(cartItems).reduce(
      (sum, item) => sum + item.price * item.quantity,
      0,
    );
    
    // Sync with window.cart for checkout.js
    window.cart = Object.entries(cartItems).map(([id, item]) => ({
      id: id,
      name: item.name,
      price: item.price,
      quantity: item.quantity
    }));
    
    updateAllCartTotals(totalCartAmount);
  }

  /* -------------------- 🔢 QUANTITY CONTROLS -------------------- */
  productGrid.addEventListener("click", function (e) {
    if (
      e.target.classList.contains("decrease-qty") ||
      e.target.classList.contains("increase-qty")
    ) {
      const card = e.target.closest(".product-card");
      const input = card.querySelector(".quantity-input");
      const currentValue = parseInt(input.value);
      const maxStock = parseInt(input.max);

      if (e.target.classList.contains("decrease-qty")) {
        if (currentValue > 1) input.value = currentValue - 1;
      } else {
        if (currentValue < maxStock) input.value = currentValue + 1;
      }

      updateItemTotal(card);
    }
  });

  productGrid.addEventListener("input", function (e) {
    if (e.target.classList.contains("quantity-input")) {
      const card = e.target.closest(".product-card");
      const maxStock = parseInt(e.target.max);
      let value = parseInt(e.target.value) || 1;
      value = Math.max(1, Math.min(value, maxStock));
      e.target.value = value;
      updateItemTotal(card);
    }
  });

  /* -------------------- 🛒 ADD TO CART LOGIC -------------------- */
  productGrid.addEventListener("click", async function (e) {
    if (
      e.target.classList.contains("add-to-cart") ||
      e.target.parentElement.classList.contains("add-to-cart")
    ) {
      const card = e.target.closest(".product-card");
      const productId = card.dataset.productId;
      const quantity = parseInt(card.querySelector(".quantity-input").value);
      const stockElement = card.querySelector(".stock-quantity");
      const productName = card.querySelector(".card-title").textContent;
      const currentStock = parseInt(stockElement.innerText);

      try {
        const response = await fetch("/inventory/update-stock/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ product_id: productId, quantity }),
        });

        const data = await response.json();
        if (data.success) {
          stockElement.innerText = data.new_stock;
          const quantityInput = card.querySelector(".quantity-input");
          quantityInput.max = data.new_stock;

          if (data.new_stock === 0) {
            quantityInput.disabled = true;
            e.target.disabled = true;
          }

          if (data.is_low_stock) card.classList.add("low-stock");

          if (!cartItems[productId]) {
            cartItems[productId] = {
              name: productName,
              quantity: 0,
              price: parseFloat(
                card.querySelector(".price").innerText.replace("₹", ""),
              ),
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
            showToast(message, "info");
          } else {
            const message = `🎇 Added ${quantity} × ${productName} to cart`;
            showToast(message, "success");
          }
        } else {
          showToast(data.error || "Failed to add items to cart", "danger");
        }
      } catch (error) {
        console.error("Error:", error);
        showToast("Failed to update cart. Please try again.", "danger");
      }
    }
  });

  /* -------------------- ❌ REMOVE CART ITEM -------------------- */
  cartItemsContainer.addEventListener("click", function (e) {
    if (
      e.target.classList.contains("remove-item") ||
      e.target.classList.contains("btn-remove-item") ||
      e.target.closest(".remove-item") ||
      e.target.closest(".btn-remove-item")
    ) {
      const cartItem = e.target.closest(".cart-item") || e.target.closest(".modern-cart-item");
      const itemId = cartItem?.dataset.id;
      if (itemId && cartItems[itemId]) {
        delete cartItems[itemId];
        updateCartTotal();
        updateCartCount();
        renderCartItems();
        showToast("Item removed from cart", "warning");
      }
    }
  });

  /* -------------------- 🎇 TOAST UTILITY -------------------- */
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast align-items-center text-bg-${type} border-0 show position-fixed bottom-0 end-0 m-3`;
    toast.style.zIndex = "3000";
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

  productGrid.addEventListener("mousedown", (e) => {
    if (window.innerWidth > 768) return;
    isDragging = true;
    startX = e.pageX - productGrid.offsetLeft;
    scrollLeft = productGrid.scrollLeft;
    productGrid.classList.add("dragging");
  });

  productGrid.addEventListener("mouseleave", () => {
    isDragging = false;
  });
  productGrid.addEventListener("mouseup", () => {
    isDragging = false;
    productGrid.classList.remove("dragging");
  });

  productGrid.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    e.preventDefault();
    const x = e.pageX - productGrid.offsetLeft;
    const walk = (x - startX) * 1.2;
    productGrid.scrollLeft = scrollLeft - walk;
  });

  /* -------------------- 🔄 INITIALIZATION -------------------- */
  document.querySelectorAll(".product-card").forEach(updateItemTotal);
});
