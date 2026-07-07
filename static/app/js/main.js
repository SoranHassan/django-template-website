document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.quickview-btn').forEach(button => {
        button.addEventListener('click', () => {
            const productId = button.dataset.productId;
            fetchProduct(productId);
        });
    });
});

function fetchProduct(id) {
    fetch(`/product/${id}`, {
        headers: { 'Accept': 'application/json' }
    })
    .then(async res => {
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    })
    .then(data => {

        // Basic details
        document.getElementById('product-id').value = data.id;
        document.getElementById('product-title').textContent = data.title;
        document.getElementById('product-image').src = data.img;

        // Tag
        const tagSpan = document.getElementById('product-tag');
        if (data.tag && data.style) {
            tagSpan.textContent = data.tag;
            tagSpan.className = `text-light rounded px-2 py-1 ${data.style}`;
        } else {
            tagSpan.textContent = '';
            tagSpan.className = '';
        }

        // Price and options
        updatePrice(data.price, 1, data.original_price);
        if (Array.isArray(data.colors)) setRadioOptions('color', data.colors, 'product-colors', true);
        if (Array.isArray(data.sizes))  setRadioOptions('size',  data.sizes,  'product-sizes', false);

        document.getElementById('quantity-select').value = '1';
    })
    .catch(err => {
        console.error('Fetch product failed:', err);
        alert('Failed to load product. Please try again.');
    });
}

function setRadioOptions(name, options, containerId, isColor) {
    const container = document.getElementById(containerId);
    if (!container || !Array.isArray(options)) return;

    container.innerHTML = options.map(opt => {
        const id = `${name}-${opt}`;
        return isColor
            ? `
            <div class="form-check form-option form-check-inline mb-1">
                <input class="form-check-input" type="radio" name="${name}" id="${id}" value="${opt}">
                <label class="form-option-label rounded-circle" for="${id}">
                    <span class="form-option-color rounded-circle ${opt}"></span>
                </label>
            </div>`
            : `
            <div class="form-check form-option size-option form-check-inline mb-2">
                <input class="form-check-input" type="radio" name="${name}" id="${id}" value="${opt}">
                <label class="form-option-label" for="${id}">${opt}</label>
            </div>`;
    }).join('');

    // Auto-select the first option
    const firstOption = container.querySelector('input[type="radio"]');
    if (firstOption) firstOption.checked = true;
}

function updatePrice(singlePrice, quantity, originalPrice = 0) {
    const total = (singlePrice * quantity).toFixed(2);
    const originalTotal = (originalPrice * quantity).toFixed(2);

    const priceHtml = originalPrice
        ? `<span class="ft-medium text-muted line-through fs-md me-2">$${originalTotal}</span>
           <span class="ft-bold theme-cl fs-lg me-2">$${total}</span>`
        : `<span class="ft-bold theme-cl fs-lg me-2">$${total}</span>`;

    const priceContainer = document.getElementById('product-price');
    if (priceContainer) priceContainer.innerHTML = priceHtml;
}

document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

    function updateCount(selector, count = null, fetchUrl = null) {
        if (count !== null) {
            document.querySelectorAll(selector).forEach(el => el.textContent = count);
        } else if (fetchUrl) {
            fetch(fetchUrl)
                .then(res => res.json())
                .then(data => {
                    if (data.count !== undefined) {
                        document.querySelectorAll(selector).forEach(el => el.textContent = data.count);
                    }
                })
                .catch(err => console.error(`Failed to update count from ${fetchUrl}:`, err));
        }
    }

    function updateSubtotalAndTotal(fetchUrl = '/cart/subtotal') {
        fetch(fetchUrl)
            .then(res => res.json())
            .then(data => {
                const formattedSubtotal = `$${parseFloat(data.subtotal).toFixed(2)}`;
                const formattedTax = `$${parseFloat(data.tax || 0).toFixed(2)}`;
                const formattedTotal = `$${parseFloat(data.total || 0).toFixed(2)}`;

                document.querySelectorAll('#cart-subtotal').forEach(el => el.textContent = formattedSubtotal);
                document.querySelectorAll('#cart-tax').forEach(el => el.textContent = formattedTax);
                document.querySelectorAll('#cart-total').forEach(el => el.textContent = formattedTotal);
            })
            .catch(err => console.error(`Subtotal/Total update failed:`, err));
    }
    
    function updateSubtotal(fetchUrl = '/wishlist/subtotal') {
        fetch(fetchUrl)
            .then(res => res.json())
            .then(data => {
                const formattedSubtotal = `$${parseFloat(data.subtotal).toFixed(2)}`;

                document.querySelectorAll('#wishlist-subtotal').forEach(el => el.textContent = formattedSubtotal);
            })
            .catch(err => console.error(`Subtotal update failed:`, err));
    }

    function refreshSidebar(containerSelector, fetchUrl, emptyMessage, bindCallback) {
        fetch(fetchUrl)
            .then(res => res.text())
            .then(html => {
                const newContent = new DOMParser()
                    .parseFromString(html, 'text/html')
                    .querySelector(containerSelector);
                const target = document.querySelector(containerSelector);
                if (target && newContent) {
                    target.innerHTML = newContent.innerHTML;
                    bindCallback?.();
                }
            })
            .catch(err => console.error(`${containerSelector} refresh failed:`, err));
    }

    function gatherProductData(context = 'cart') {
        const id = document.getElementById('product-id')?.value;
        const title = document.getElementById('product-title')?.textContent;
        const image = document.getElementById('product-image')?.src;
        const price = document.querySelector('#product-price .theme-cl')?.textContent.replace('$', '');
        const size = document.querySelector("input[name='size']:checked")?.value;
        const color = document.querySelector("input[name='color']:checked")?.value;
        const quantity = document.getElementById('quantity-select')?.value;

        if (!id || !title || !image || !price || !size || !color || !quantity) {
            alert(`Please complete all selections before adding to ${context}.`);
            return null;
        }

        return { id, title, image, price, size, color, quantity };
    }

    function addToList(event, type = 'cart') {
        const button = event.currentTarget;
        const product = gatherProductData(type);
        if (!product || !csrfToken) return;

        button.disabled = true;
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="lni lni-spinner fa-spin me-2"></i>Adding...';

        fetch(`/${type}/add`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(product)
        })
            .then(res => res.json())
            .then(data => {
                if (!data || !data.message) throw data;

                // Show toast instead of alert or sidebar open
                Toastify({
                    text: `Your product was added to ${type === 'cart' ? '🛒 Cart' : '💖 Wishlist'} successfully!`,
                    duration: 1000,
                    gravity: "top",
                    position: "right",
                    stopOnFocus: true,
                    style: {
                        background: "linear-gradient(to right, #00b09b, #96c93d)",
                        color: "#fff",
                        fontWeight: "bold",
                    },
                }).showToast();

                if (type === 'cart') {
                    refreshCart();
                } else {
                    refreshWishlist();
                }

                updateCount(`.${type}-count`, null, `/${type}/count`);

                const modal = document.getElementById('quickview');
                bootstrap.Modal.getInstance(modal)?.hide();
            })
            .catch(err => {
                console.error(`Add to ${type} error:`, err);
                alert(err.message || `Error adding to ${type}.`);
            })
            .finally(() => {
                button.disabled = false;
                button.innerHTML = originalHTML;
            });
    }

    function bindRemoveButtons(type = 'cart') {
        const selector = `.close_${type}_item`;
        document.querySelectorAll(selector).forEach(button => {
            button.addEventListener('click', () => {
                const id = button.getAttribute('data-id');
                const itemWrapper = button.closest(`.${type}-item-wrapper`);

                fetch(`/${type}/remove`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ id })
                })
                    .then(res => res.json())
                    .then(({ success, subtotal, [`${type}Count`]: count }) => {
                        if (success) {
                            itemWrapper.remove();

                            if (type === 'cart') {
                                refreshCart();
                                updateSubtotalAndTotal('/cart/subtotal');
                            } else if (type === 'wishlist') {
                                refreshWishlist();
                                updateSubtotal('/wishlist/subtotal');
                                refreshWishlistSidebar();
                                refreshWishlistPage();
                            }

                            updateCount(`.${type}-count`, count);

                            if (count === 0) {
                            const sidebarItems = document.querySelectorAll(`.${type}_select_items`);
                            sidebarItems.forEach(el => {
                                el.innerHTML = `<p class="px-3 py-3">Your ${type} is empty.</p>`;
                            });

                            const fullPageWrapper = document.querySelectorAll(`.${type}-content-wrapper`);
                            fullPageWrapper.forEach(el => {
                                el.innerHTML = `
                                    <div class="d-flex flex-column justify-content-center align-items-center text-center" style="min-height: 400px;">
                                        <div>
                                            <img src="/static/app/img/${type}.png" class="img-fluid" width="100" alt="" />
                                        </div>
                                        <h2 class="mt-2 mb-2 ft-bold">Your ${type} is empty!</h2>
                                        <p class="text-muted fs-6">Your ${type} is empty. Please go to the shop page and buy your favourite items.</p>
                                        <div class="position-relative text-center">
                                            <a href="{% url 'App:shop_style_1' %}" class="btn stretched-links borders">Shop Now</a>
                                        </div>
                                    </div>
                                `;
                            });
                        }
                    } else {
                        alert(`Failed to remove item from ${type}.`);
                    }
                    })
                    .catch(err => {
                        console.error(`${type} remove error:`, err);
                        alert(`An error occurred while removing the item from ${type}.`);
                    });
            });
        });
    }

    function refreshWishlistSidebar() {
        fetch('/wishlist/sidebar')
            .then(res => res.text())
            .then(html => {
                const parser = new DOMParser();
                const newDoc = parser.parseFromString(html, 'text/html');
                const newContent = newDoc.querySelector('#wishlist-content');
                if (newContent) {
                    document.querySelector('#wishlist-content').innerHTML = newContent.innerHTML;
                    bindRemoveButtons('wishlist');
                }
            })
            .catch(err => console.error('Failed to refresh wishlist sidebar:', err));
    }

    function moveWishlistItemToCart(button) {
        const wrapper = button.closest('.wishlist-item-wrapper');
        const id = wrapper?.getAttribute('data-id');
        const title = wrapper?.querySelector('.product_title')?.textContent?.trim() ||
                      wrapper?.querySelector('h5 a')?.textContent?.trim();
        const image = wrapper?.querySelector('img')?.src;
        const price = wrapper?.querySelector('.price')?.getAttribute('data-price');

        const size = wrapper?.querySelector('.product-size')?.textContent?.trim() || '28';
        const color = wrapper?.querySelector('.product-color')?.textContent?.trim() || 'yellow';
        const quantityText = wrapper?.querySelector('.bg-gray-200')?.textContent || 'Qty: 1';
        const quantity = quantityText.replace('Qty:', '').trim() || '1';

        if (!id || !title || !image || !price) {
            alert('Missing product data. Cannot add to cart.');
            return;
        }

        const data = { id, title, image, price, size, color, quantity };

        fetch('/cart/add', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(res => res.json())
        .then(res => {
            if (!res.success && !res.message) throw res;
            refreshCart();
            updateCount('.cart-count', null, '/cart/count');
            updateSubtotalAndTotal();

            return fetch('/wishlist/remove', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id })
            });
        })
        .then(res => res.json())
        .then(res => {
            if (res.success) {
                refreshWishlist();
                refreshWishlistPage();
                updateCount('.wishlist-count', null, '/wishlist/count');
            } else {
                alert('Failed to remove from wishlist after adding to cart.');
            }
        })
        .catch(err => {
            console.error('Move wishlist to cart failed:', err);
            alert('Something went wrong while moving to cart.');
        });
    }

    document.querySelectorAll('.add_wishlist_item').forEach(button => {
        button.addEventListener('click', () => moveWishlistItemToCart(button));
    });

    window.refreshWishlist = () => {
        refreshSidebar('#wishlist-content', '/wishlist/sidebar', 'Your wishlist is empty.', () => {
            bindRemoveButtons('wishlist');
            document.querySelectorAll('.add_wishlist_item').forEach(button => {
                button.addEventListener('click', () => moveWishlistItemToCart(button));
            });
        });
        updateSubtotal();
    };

    window.refreshWishlistPage = () => {
        fetch('/wishlist')
            .then(res => res.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');

                const newContent = doc.querySelector('#wishlist-content-wrapper');

                const currentContent = document.querySelector('#wishlist-content-wrapper');
                if (newContent && currentContent) {
                    currentContent.innerHTML = newContent.innerHTML;
                }

                bindRemoveButtons('wishlist');
                document.querySelectorAll('.add_wishlist_item').forEach(button => {
                    button.addEventListener('click', () => moveWishlistItemToCart(button));
                });
            })
            .catch(err => {
                console.error('Failed to refresh wishlist page:', err);
            });
    };

    window.refreshCart = () => {
        refreshSidebar('#cart-content', '/cart/sidebar', 'Your cart is empty.', () => {
            bindRemoveButtons('cart');
        });

        updateSubtotalAndTotal();

        const cartPageWrapper = document.querySelector('.cart-content-wrapper');
        if (cartPageWrapper) {
            fetch('/cart/page')
                .then(res => res.text())
                .then(html => {
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const updated = doc.querySelector('.cart-content-wrapper');
                    if (updated) {
                        cartPageWrapper.innerHTML = updated.innerHTML;
                        bindRemoveButtons('cart');

                        document.querySelectorAll('.quantity-select').forEach(select => {
                            select.addEventListener('change', function () {
                                const id = this.dataset.id;
                                const quantity = this.value;

                                fetch('/cart/update', {
                                    method: 'POST',
                                    headers: {
                                        'X-CSRFToken': csrfToken,
                                        'Content-Type': 'application/json'
                                    },
                                    body: JSON.stringify({ id, quantity })
                                })
                                    .then(res => res.json())
                                    .then(data => {
                                        if (data.success) {
                                            updateSubtotalAndTotal('/cart/subtotal');
                                            updateCount('.cart-count', data.cartCount || null);
                                            refreshCart();
                                        } else {
                                            alert('Failed to update quantity.');
                                        }
                                    })
                                    .catch(err => {
                                        console.error('Quantity update error:', err);
                                        alert('An error occurred while updating quantity.');
                                    });
                            });
                        });
                    }
                })
                .catch(err => console.error('Cart page refresh error:', err));
        }
    };

    window.addToCart = (e) => addToList(e, 'cart');
    window.addToWishlist = (e) => addToList(e, 'wishlist');

    bindRemoveButtons('cart');
    bindRemoveButtons('wishlist');

    updateCount('.cart-count', null, '/cart/count');
    updateCount('.wishlist-count', null, '/wishlist/count');

    document.querySelectorAll('.quantity-select').forEach(select => {
        select.addEventListener('change', function () {
            const id = this.dataset.id;
            const quantity = this.value;

            fetch('/cart/update', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ id, quantity })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        updateSubtotalAndTotal('/cart/subtotal');
                        updateCount('.cart-count', data.cartCount || null);
                        refreshCart();
                    } else {
                        alert('Failed to update quantity.');
                    }
                })
                .catch(err => {
                    console.error('Quantity update error:', err);
                    alert('An error occurred while updating quantity.');
                });
        });
    });
});