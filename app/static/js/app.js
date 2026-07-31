// Pioneer Flow - Application Controller
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});

const app = {
    // Current application state
    state: {
        activeSection: 'dashboard',
        customers: [],
        products: [],
        invoiceItems: [], // List of {product_id, part_number, part_name, quantity, current_stock, unit_price_100, discount_percentage}
        selectedCustomer: null, // If existing customer is selected
        selectedProduct: null,  // Currently selected product from catalog autocomplete
        gstRate: 18.0
    },

    init() {
        this.setupNavigation();
        this.setupDashboard();
        this.setupImports();
        this.setupProductsCatalog();
        this.setupCustomers();
        this.setupInvoiceCreator();
        this.setupSettings();
        
        // Load initial dashboard
        this.loadSection('dashboard');
    },

    // Navigation logic
    setupNavigation() {
        const menuItems = document.querySelectorAll('.menu-item');
        menuItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const section = item.getAttribute('data-section');
                this.loadSection(section);
                
                // Active class toggling
                menuItems.forEach(i => i.classList.remove('active'));
                item.classList.add('active');
            });
        });
    },

    loadSection(sectionId) {
        this.state.activeSection = sectionId;
        
        // Hide all sections
        document.querySelectorAll('.content-section').forEach(sec => {
            sec.classList.remove('active');
        });
        
        // Show target section
        const targetSection = document.getElementById(`section-${sectionId}`);
        if (targetSection) {
            targetSection.classList.add('active');
        }

        // Close invoice view if open
        this.closeInvoiceView();

        // Update titles
        const titleEl = document.getElementById('header-section-title');
        const descEl = document.getElementById('header-section-desc');
        
        switch(sectionId) {
            case 'dashboard':
                titleEl.textContent = 'Dashboard Overview';
                descEl.textContent = 'Operational stats and data synchronisation status';
                this.loadDashboardStats();
                break;
            case 'imports':
                titleEl.textContent = 'Import Data Sheets';
                descEl.textContent = 'Import inventory lists and product price sheets from Excel';
                this.loadImportHistory();
                break;
            case 'products':
                titleEl.textContent = 'Product Catalog';
                descEl.textContent = 'View and search products, stock levels, and active prices';
                this.loadProductCatalog();
                break;
            case 'customers':
                titleEl.textContent = 'Customer Registry';
                descEl.textContent = 'Create and manage default discount profiles and billing GST details';
                this.loadCustomersRegistry();
                this.resetCustomerForm();
                break;
            case 'invoice-creator':
                titleEl.textContent = 'Generate Tax Invoice';
                descEl.textContent = 'Verify stock and automatically generate tax compliant invoices';
                this.resetInvoiceCreator();
                break;
            case 'invoice-history':
                titleEl.textContent = 'Invoice Logs & Archives';
                descEl.textContent = 'Retrieve and reprint previously generated customer invoices';
                this.loadInvoiceHistory();
                break;
            case 'settings':
                titleEl.textContent = 'System Settings';
                descEl.textContent = 'Manage application-wide settings and default configurations';
                this.loadSettings();
                break;
        }
    },

    // --- DASHBOARD MODULE ---
    setupDashboard() {
        // Nothing special to bind, dynamically loaded
    },

    loadDashboardStats() {
        fetch('/api/dashboard/stats')
            .then(res => res.json())
            .then(data => {
                document.getElementById('dash-total-products').textContent = data.total_products;
                document.getElementById('dash-total-customers').textContent = data.total_customers;
                document.getElementById('dash-total-invoices').textContent = data.total_invoices;
                
                const lastInv = data.last_inventory_import;
                document.getElementById('dash-last-inventory').textContent = lastInv ? new Date(lastInv).toLocaleString() : 'Never';
                
                const lastPrice = data.last_price_import;
                document.getElementById('dash-last-price').textContent = lastPrice ? new Date(lastPrice).toLocaleString() : 'Never';
            });
            
        // Load recent import activity
        fetch('/api/import/logs')
            .then(res => res.json())
            .then(logs => {
                const tbody = document.getElementById('dash-import-logs');
                tbody.innerHTML = '';
                if (logs.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center">No logs recorded yet.</td></tr>';
                    return;
                }
                logs.slice(0, 5).forEach(log => {
                    const statusClass = log.status === 'success' ? 'badge-success' : (log.status === 'partial_success' ? 'badge-warning' : 'badge-danger');
                    const statusText = log.status === 'success' ? 'Success' : (log.status === 'partial_success' ? 'Partial' : 'Failed');
                    
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${new Date(log.imported_at).toLocaleDateString()}</td>
                        <td><span class="badge badge-info">${log.import_type.toUpperCase()}</span></td>
                        <td>${log.filename}</td>
                        <td>${log.total_records}</td>
                        <td>${log.successful_records}</td>
                        <td><span class="badge ${statusClass}">${statusText}</span></td>
                    `;
                    tbody.appendChild(tr);
                });
            });
    },

    // --- IMPORTS MODULE ---
    setupImports() {
        const bindUploadForm = (formId, endpoint, resultId) => {
            const form = document.getElementById(formId);
            const resultBox = document.getElementById(resultId);
            
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                resultBox.classList.add('hidden');
                
                const formData = new FormData(form);
                
                fetch(endpoint, {
                    method: 'POST',
                    body: formData
                })
                .then(res => res.json())
                .then(data => {
                    resultBox.className = 'import-summary-box';
                    if (data.status === 'success') {
                        resultBox.classList.add('success');
                    } else if (data.status === 'partial_success') {
                        resultBox.classList.add('partial');
                    } else {
                        resultBox.classList.add('failed');
                    }
                    
                    let errorListHtml = '';
                    if (data.errors && data.errors.length > 0) {
                        errorListHtml = `
                            <strong>Skipped Row Errors (${data.errors.length}):</strong>
                            <ul>
                                ${data.errors.map(err => `<li>${err}</li>`).join('')}
                            </ul>
                        `;
                    }
                    
                    resultBox.innerHTML = `
                        <strong>Import Completed (${data.status.toUpperCase()})</strong><br>
                        Total Rows Processed: ${data.total_records}<br>
                        Successful Entries: ${data.successful_records}<br>
                        Failed Rows: ${data.failed_records}<br>
                        ${errorListHtml}
                    `;
                    resultBox.classList.remove('hidden');
                    
                    form.reset();
                    this.loadImportHistory();
                })
                .catch(err => {
                    resultBox.className = 'import-summary-box failed';
                    resultBox.innerHTML = `<strong>Error:</strong> Failed to connect to server. ${err}`;
                    resultBox.classList.remove('hidden');
                });
            });
        };
        
        bindUploadForm('form-import-inventory', '/api/import/inventory', 'inv-inventory-result');
        bindUploadForm('form-import-cost', '/api/import/cost', 'cost-import-result');
    },

    loadImportHistory() {
        fetch('/api/import/logs')
            .then(res => res.json())
            .then(logs => {
                const tbody = document.getElementById('import-history-table');
                tbody.innerHTML = '';
                if (logs.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center">No upload history found.</td></tr>';
                    return;
                }
                logs.forEach(log => {
                    const statusClass = log.status === 'success' ? 'badge-success' : (log.status === 'partial_success' ? 'badge-warning' : 'badge-danger');
                    const statusText = log.status === 'success' ? 'Success' : (log.status === 'partial_success' ? 'Partial' : 'Failed');
                    
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${new Date(log.imported_at).toLocaleString()}</td>
                        <td><span class="badge badge-info">${log.import_type.toUpperCase()}</span></td>
                        <td>${log.filename}</td>
                        <td>${log.total_records}</td>
                        <td>${log.successful_records}</td>
                        <td>${log.failed_records}</td>
                        <td><span class="badge ${statusClass}">${statusText}</span></td>
                    `;
                    tbody.appendChild(tr);
                });
            });
    },

    // --- PRODUCTS CATALOG MODULE ---
    setupProductsCatalog() {
        const searchInput = document.getElementById('product-search-input');
        let debounceTimer;
        
        searchInput.addEventListener('keyup', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                this.loadProductCatalog(searchInput.value);
            }, 300);
        });
    },

    loadProductCatalog(query = '') {
        fetch(`/api/products/search?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(products => {
                const tbody = document.getElementById('catalog-products-table');
                tbody.innerHTML = '';
                if (products.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" class="text-center">No matching products found in catalog.</td></tr>';
                    return;
                }
                products.forEach(p => {
                    const priceFormatted = p.price_per_100_pcs ? `₹${p.price_per_100_pcs.toFixed(2)}` : '₹0.00';
                    const stockClass = p.current_stock > 10 ? 'badge-success' : (p.current_stock > 0 ? 'badge-warning' : 'badge-danger');
                    
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>${p.part_number}</strong></td>
                        <td>${p.make || '-'}</td>
                        <td>${p.series || '-'}</td>
                        <td>${p.packing_quantity}</td>
                        <td>${p.unit}</td>
                        <td><span class="badge ${stockClass}">${p.current_stock}</span></td>
                        <td>${priceFormatted}</td>
                    `;
                    tbody.appendChild(tr);
                });
            });
    },

    // --- CUSTOMERS REGISTRY MODULE ---
    setupCustomers() {
        const form = document.getElementById('form-customer');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const custId = document.getElementById('cust-id').value;
            const name = document.getElementById('cust-name').value;
            const discount = document.getElementById('cust-discount').value;
            const gst = document.getElementById('cust-gst').value;
            const terms = document.getElementById('cust-terms').value;
            
            const payload = {
                name: name,
                discount_percentage: discount,
                gst_number: gst,
                payment_terms: terms
            };
            
            const isEdit = custId !== '';
            const url = isEdit ? `/api/customers/${custId}` : '/api/customers';
            const method = isEdit ? 'PUT' : 'POST';
            
            fetch(url, {
                method: method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    return;
                }
                this.loadCustomersRegistry();
                this.resetCustomerForm();
            })
            .catch(err => alert(`Network error saving customer: ${err}`));
        });
    },

    resetCustomerForm() {
        document.getElementById('cust-id').value = '';
        document.getElementById('cust-name').value = '';
        document.getElementById('cust-discount').value = '0';
        document.getElementById('cust-gst').value = '';
        document.getElementById('cust-terms').value = '';
        document.getElementById('customer-form-title').textContent = 'Add New Customer';
        document.getElementById('cust-submit-btn').textContent = 'Save Customer';
        document.getElementById('cust-cancel-btn').classList.add('hidden');
    },

    loadCustomersRegistry() {
        fetch('/api/customers')
            .then(res => res.json())
            .then(customers => {
                const tbody = document.getElementById('registry-customers-table');
                tbody.innerHTML = '';
                if (customers.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" class="text-center">No customers registered yet.</td></tr>';
                    return;
                }
                customers.forEach(c => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>${c.name}</strong></td>
                        <td>${c.discount_percentage.toFixed(2)}%</td>
                        <td>${c.gst_number || '-'}</td>
                        <td>${c.payment_terms || '-'}</td>
                        <td>
                            <button class="btn btn-outline" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;" onclick="app.editCustomer(${c.id})">
                                <i class="fa-solid fa-edit"></i> Edit
                            </button>
                            <button class="btn btn-danger" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;" onclick="app.deleteCustomer(${c.id})">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            });
    },

    editCustomer(id) {
        fetch(`/api/customers/${id}`)
            .then(res => res.json())
            .then(c => {
                document.getElementById('cust-id').value = c.id;
                document.getElementById('cust-name').value = c.name;
                document.getElementById('cust-discount').value = c.discount_percentage;
                document.getElementById('cust-gst').value = c.gst_number || '';
                document.getElementById('cust-terms').value = c.payment_terms || '';
                
                document.getElementById('customer-form-title').textContent = 'Edit Customer Details';
                document.getElementById('cust-submit-btn').textContent = 'Update Customer';
                document.getElementById('cust-cancel-btn').classList.remove('hidden');
            });
    },

    deleteCustomer(id) {
        if (!confirm('Are you sure you want to delete this customer?')) return;
        
        fetch(`/api/customers/${id}`, {
            method: 'DELETE'
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(`Error: ${data.error}`);
                return;
            }
            this.loadCustomersRegistry();
        })
        .catch(err => alert(`Network error: ${err}`));
    },

    // --- INVOICE CREATOR MODULE ---
    setupInvoiceCreator() {
        // Customer Auto-complete binding
        const custSearch = document.getElementById('inv-customer-search');
        const custDropdown = document.getElementById('customer-autocomplete-dropdown');
        
        custSearch.addEventListener('input', () => {
            const val = custSearch.value.trim();
            if (val.length < 1) {
                custDropdown.classList.add('hidden');
                this.updateCustomerBadges(false, false);
                return;
            }
            
            fetch(`/api/customers?q=${encodeURIComponent(val)}`)
                .then(res => res.json())
                .then(customers => {
                    custDropdown.innerHTML = '';
                    if (customers.length === 0) {
                        custDropdown.classList.add('hidden');
                        this.updateCustomerBadges(false, true); // new customer
                        this.state.selectedCustomer = null;
                        return;
                    }
                    
                    customers.forEach(c => {
                        const item = document.createElement('div');
                        item.className = 'autocomplete-item';
                        item.textContent = c.name;
                        item.addEventListener('click', () => {
                            custSearch.value = c.name;
                            document.getElementById('inv-cust-discount').value = c.discount_percentage;
                            document.getElementById('inv-cust-gst').value = c.gst_number || '';
                            document.getElementById('inv-cust-terms').value = c.payment_terms || '';
                            
                            this.state.selectedCustomer = c;
                            custDropdown.classList.add('hidden');
                            this.updateCustomerBadges(true, false);
                            
                            // Recompute invoice since customer discount changes default rates
                            this.recalculateInvoice();
                        });
                        custDropdown.appendChild(item);
                    });
                    custDropdown.classList.remove('hidden');
                });
        });
        
        // Hide autocomplete when clicking elsewhere
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.customer-autocomplete-container')) {
                custDropdown.classList.add('hidden');
            }
            if (!e.target.closest('.product-lookup-row')) {
                document.getElementById('product-autocomplete-dropdown').classList.add('hidden');
            }
        });

        // Product Auto-complete binding
        const prodSearch = document.getElementById('inv-product-search');
        const prodDropdown = document.getElementById('product-autocomplete-dropdown');
        
        prodSearch.addEventListener('input', () => {
            const val = prodSearch.value.trim();
            if (val.length < 1) {
                prodDropdown.classList.add('hidden');
                this.clearProductLookup();
                return;
            }
            
            fetch(`/api/products/search?q=${encodeURIComponent(val)}`)
                .then(res => res.json())
                .then(products => {
                    prodDropdown.innerHTML = '';
                    if (products.length === 0) {
                        prodDropdown.classList.add('hidden');
                        this.clearProductLookup();
                        return;
                    }
                    
                    products.forEach(p => {
                        const item = document.createElement('div');
                        item.className = 'autocomplete-item';
                        item.innerHTML = `
                            <span><strong>${p.part_number}</strong> (${p.make || 'WAGO'})</span>
                            <span class="stock-info">Stock: ${p.current_stock}</span>
                        `;
                        item.addEventListener('click', () => {
                            prodSearch.value = p.part_number;
                            document.getElementById('lookup-price-display').value = `₹${p.price_per_100_pcs.toFixed(2)}`;
                            document.getElementById('lookup-stock-display').value = p.current_stock;
                            
                            this.state.selectedProduct = p;
                            prodDropdown.classList.add('hidden');
                        });
                        prodDropdown.appendChild(item);
                    });
                    prodDropdown.classList.remove('hidden');
                });
        });

        // Set default invoice date to today
        document.getElementById('inv-date').value = new Date().toISOString().substring(0, 10);
    },

    updateCustomerBadges(isExisting, isNew) {
        const badgeExist = document.getElementById('cust-badge');
        const badgeNew = document.getElementById('cust-badge-new');
        
        if (isExisting) {
            badgeExist.classList.remove('hidden');
            badgeNew.classList.add('hidden');
        } else if (isNew) {
            badgeExist.classList.add('hidden');
            badgeNew.classList.remove('hidden');
        } else {
            badgeExist.classList.add('hidden');
            badgeNew.classList.add('hidden');
        }
    },

    clearProductLookup() {
        this.state.selectedProduct = null;
        document.getElementById('lookup-price-display').value = '';
        document.getElementById('lookup-stock-display').value = '';
    },

    addItemFromLookup() {
        if (!this.state.selectedProduct) {
            alert('Please search and select a product from the list first.');
            return;
        }
        
        const qtyInput = document.getElementById('lookup-qty');
        const discInput = document.getElementById('lookup-disc');
        
        const qty = parseInt(qtyInput.value);
        if (isNaN(qty) || qty <= 0) {
            alert('Please enter a valid positive quantity.');
            return;
        }
        
        const p = this.state.selectedProduct;
        
        // Custom discount overrides fallback customer discount
        let disc = discInput.value.trim();
        if (disc !== '') {
            disc = parseFloat(disc);
            if (isNaN(disc) || disc < 0 || disc > 100) {
                alert('Please enter a valid discount percentage between 0 and 100.');
                return;
            }
        } else {
            disc = null; // Use customer default
        }

        // Check if item already exists in local list, update it
        const existingIdx = this.state.invoiceItems.findIndex(i => i.product_id === p.id);
        if (existingIdx !== -1) {
            this.state.invoiceItems[existingIdx].quantity += qty;
            if (disc !== null) {
                this.state.invoiceItems[existingIdx].discount_percentage = disc;
            }
        } else {
            this.state.invoiceItems.push({
                product_id: p.id,
                part_number: p.part_number,
                part_name: p.part_name || p.part_number,
                quantity: qty,
                current_stock: p.current_stock,
                unit_price_100: p.price_per_100_pcs,
                discount_percentage: disc
            });
        }
        
        // Reset lookup inputs
        document.getElementById('inv-product-search').value = '';
        qtyInput.value = '1';
        discInput.value = '';
        this.clearProductLookup();
        
        // Recalculate
        this.recalculateInvoice();
    },

    removeInvoiceItem(idx) {
        this.state.invoiceItems.splice(idx, 1);
        this.recalculateInvoice();
    },

    updateInvoiceItemQty(idx, newQty) {
        const qty = parseInt(newQty);
        if (isNaN(qty) || qty <= 0) return;
        this.state.invoiceItems[idx].quantity = qty;
        this.recalculateInvoice();
    },

    updateInvoiceItemDiscount(idx, newDisc) {
        if (newDisc === '') {
            this.state.invoiceItems[idx].discount_percentage = null;
        } else {
            const disc = parseFloat(newDisc);
            if (isNaN(disc) || disc < 0 || disc > 100) return;
            this.state.invoiceItems[idx].discount_percentage = disc;
        }
        this.recalculateInvoice();
    },

    recalculateInvoice() {
        const tbody = document.getElementById('invoice-items-body');
        
        if (this.state.invoiceItems.length === 0) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="7" class="text-center">No items added to invoice yet.</td></tr>';
            document.getElementById('summary-subtotal').textContent = '₹0.00';
            document.getElementById('summary-gst-amount').textContent = '₹0.00';
            document.getElementById('summary-grand-total').textContent = '₹0.00';
            document.getElementById('stock-warnings-box').classList.add('hidden');
            return;
        }
        
        // Load values
        const custName = document.getElementById('inv-customer-search').value.trim();
        const custDiscount = parseFloat(document.getElementById('inv-cust-discount').value || 0);
        const custGst = document.getElementById('inv-cust-gst').value.trim();
        const custTerms = document.getElementById('inv-cust-terms').value.trim();
        
        const payload = {
            customer: {
                name: custName,
                discount_percentage: custDiscount,
                gst_number: custGst,
                payment_terms: custTerms
            },
            items: this.state.invoiceItems.map(i => ({
                product_id: i.product_id,
                quantity: i.quantity,
                discount_percentage: i.discount_percentage
            }))
        };
        
        fetch('/api/invoices/calculate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(`Error during calculation: ${data.error}`);
                return;
            }
            
            // Render table
            tbody.innerHTML = '';
            data.items.forEach((item, idx) => {
                const stockWarningClass = item.insufficient_stock ? 'badge-danger' : 'badge-success';
                const rowDisc = this.state.invoiceItems[idx].discount_percentage;
                const discPlaceholder = rowDisc === null ? `(${custDiscount.toFixed(1)}%)` : '';
                const discVal = rowDisc === null ? '' : rowDisc;
                
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${item.part_number}</strong></td>
                    <td><span class="badge ${stockWarningClass}">${item.current_stock}</span></td>
                    <td>
                        <input type="number" class="w-full text-center" style="padding: 0.2rem; background: var(--bg-input); border: 1px solid var(--border-input); color: #fff;" 
                            value="${item.quantity}" min="1" onchange="app.updateInvoiceItemQty(${idx}, this.value)">
                    </td>
                    <td>₹${item.unit_price_100.toFixed(2)}</td>
                    <td>
                        <input type="number" class="w-full text-center" style="padding: 0.2rem; background: var(--bg-input); border: 1px solid var(--border-input); color: #fff;"
                            value="${discVal}" placeholder="${discPlaceholder}" min="0" max="100" step="0.01" onchange="app.updateInvoiceItemDiscount(${idx}, this.value)">
                    </td>
                    <td><strong>₹${item.line_total.toFixed(2)}</strong></td>
                    <td>
                        <button class="btn btn-danger" style="padding: 0.2rem 0.4rem; font-size: 0.8rem;" onclick="app.removeInvoiceItem(${idx})">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            
            // Set pricing summaries
            document.getElementById('summary-subtotal').textContent = `₹${data.subtotal.toFixed(2)}`;
            document.getElementById('summary-gst-rate').textContent = data.gst_rate.toFixed(1);
            document.getElementById('summary-gst-amount').textContent = `₹${data.gst_amount.toFixed(2)}`;
            document.getElementById('summary-grand-total').textContent = `₹${data.grand_total.toFixed(2)}`;
            
            // Set stock warnings
            const warningBox = document.getElementById('stock-warnings-box');
            const warningList = document.getElementById('stock-warnings-list');
            warningList.innerHTML = '';
            
            if (data.has_warnings) {
                data.items.forEach(item => {
                    if (item.insufficient_stock) {
                        const li = document.createElement('li');
                        li.innerHTML = `Product <strong>${item.part_number}</strong>: Requested ${item.quantity}, but only ${item.current_stock} is available.`;
                        warningList.appendChild(li);
                    }
                });
                warningBox.classList.remove('hidden');
            } else {
                warningBox.classList.add('hidden');
            }
        })
        .catch(err => console.error("Recalculation fetch error: ", err));
    },

    resetInvoiceCreator() {
        document.getElementById('inv-customer-search').value = '';
        document.getElementById('inv-cust-discount').value = '0';
        document.getElementById('inv-cust-gst').value = '';
        document.getElementById('inv-cust-terms').value = '';
        this.updateCustomerBadges(false, false);
        
        this.state.selectedCustomer = null;
        this.state.selectedProduct = null;
        this.state.invoiceItems = [];
        
        document.getElementById('inv-product-search').value = '';
        this.clearProductLookup();
        this.recalculateInvoice();
    },

    showNewInvoiceCreator() {
        this.loadSection('invoice-creator');
        // Toggle side menu active highlight
        document.querySelectorAll('.menu-item').forEach(i => {
            i.classList.remove('active');
            if (i.getAttribute('data-section') === 'invoice-creator') {
                i.classList.add('active');
            }
        });
    },

    submitInvoice() {
        const custName = document.getElementById('inv-customer-search').value.trim();
        const custDiscount = parseFloat(document.getElementById('inv-cust-discount').value || 0);
        const custGst = document.getElementById('inv-cust-gst').value.trim();
        const custTerms = document.getElementById('inv-cust-terms').value.trim();
        const invDate = document.getElementById('inv-date').value;
        
        if (!custName) {
            alert('Please enter or select a customer name.');
            return;
        }
        
        if (this.state.invoiceItems.length === 0) {
            alert('Cannot generate an invoice with zero items. Please add at least one catalog item.');
            return;
        }
        
        const payload = {
            customer: {
                id: this.state.selectedCustomer ? this.state.selectedCustomer.id : null,
                name: custName,
                discount_percentage: custDiscount,
                gst_number: custGst,
                payment_terms: custTerms
            },
            items: this.state.invoiceItems.map(i => ({
                product_id: i.product_id,
                quantity: i.quantity,
                discount_percentage: i.discount_percentage
            })),
            invoice_date: invDate
        };
        
        fetch('/api/invoices', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(invoice => {
            if (invoice.error) {
                alert(`Error saving invoice: ${invoice.error}`);
                return;
            }
            // Display Generated print page
            this.showInvoicePrintPreview(invoice);
        })
        .catch(err => alert(`Network failure generating invoice: ${err}`));
    },

    // --- INVOICE HISTORY TIMELINE ---
    setupInvoiceHistory() {
        const searchInput = document.getElementById('history-search-input');
        let debounceTimer;
        
        searchInput.addEventListener('keyup', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                this.loadInvoiceHistory(searchInput.value);
            }, 300);
        });
    },

    loadInvoiceHistory(query = '') {
        fetch(`/api/invoices?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(invoices => {
                const tbody = document.getElementById('invoice-history-table-body');
                tbody.innerHTML = '';
                if (invoices.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center">No matching generated invoices found in logs.</td></tr>';
                    return;
                }
                invoices.forEach(inv => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>${inv.invoice_number}</strong></td>
                        <td>${inv.invoice_date}</td>
                        <td>${inv.customer_name_snapshot}</td>
                        <td>${inv.order_number}</td>
                        <td><strong>₹${inv.grand_total.toFixed(2)}</strong></td>
                        <td>
                            <button class="btn btn-outline" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;" onclick="app.viewInvoiceById(${inv.id})">
                                <i class="fa-solid fa-eye"></i> View & Print
                            </button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            });
    },

    viewInvoiceById(id) {
        fetch(`/api/invoices/${id}`)
            .then(res => res.json())
            .then(invoice => {
                this.showInvoicePrintPreview(invoice);
            });
    },

    // --- PRINT PREVIEW DRAW CONTROLLER ---
    showInvoicePrintPreview(invoice) {
        document.getElementById('print-invoice-num').textContent = invoice.invoice_number;
        document.getElementById('print-invoice-date').textContent = invoice.invoice_date;
        document.getElementById('print-invoice-order-ref').textContent = invoice.order.order_number;
        
        document.getElementById('print-customer-name').textContent = invoice.order.customer_name_snapshot;
        document.getElementById('print-customer-gst').textContent = invoice.order.customer_gst_snapshot || 'N/A';
        document.getElementById('print-customer-terms').textContent = invoice.order.customer_terms_snapshot || 'Due on Receipt';
        
        // Render print lines
        const tbody = document.getElementById('print-items-body');
        tbody.innerHTML = '';
        
        invoice.items.forEach((item, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${index + 1}</td>
                <td><strong>${item.part_number_snapshot}</strong></td>
                <td>WAGO</td>
                <td>PCS</td>
                <td class="text-right">${item.quantity}</td>
                <td class="text-right">₹${item.unit_price.toFixed(2)}</td>
                <td class="text-right">${item.discount_percentage.toFixed(1)}%</td>
                <td class="text-right">₹${item.line_total.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });
        
        // Subtotal, GST CGST/SGST split (India rules)
        const subtotal = invoice.order.subtotal;
        const gstRate = invoice.order.gst_rate;
        const gstAmount = invoice.order.gst_amount;
        const halfGst = gstRate / 2.0;
        const halfGstAmount = gstAmount / 2.0;
        
        document.getElementById('print-subtotal').textContent = `₹${subtotal.toFixed(2)}`;
        
        document.querySelectorAll('.half-gst-rate').forEach(el => el.textContent = halfGst.toFixed(1));
        document.getElementById('print-cgst').textContent = `₹${halfGstAmount.toFixed(2)}`;
        document.getElementById('print-sgst').textContent = `₹${halfGstAmount.toFixed(2)}`;
        
        document.getElementById('print-grand-total').textContent = `₹${invoice.order.grand_total.toFixed(2)}`;
        
        // Toggle view
        document.querySelector('.app-container').classList.add('hidden');
        document.getElementById('invoice-view-container').style.display = 'block';
    },

    closeInvoiceView() {
        document.getElementById('invoice-view-container').style.display = 'none';
        document.querySelector('.app-container').classList.remove('hidden');
    },

    // --- SETTINGS MODULE ---
    setupSettings() {
        const form = document.getElementById('form-settings');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const gst = document.getElementById('settings-gst-rate').value;
            
            fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({gst_rate: gst})
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    alert(`Error: ${data.error}`);
                    return;
                }
                alert('GST Setting updated successfully.');
                this.loadSettings();
            });
        });
    },

    loadSettings() {
        fetch('/api/settings')
            .then(res => res.json())
            .then(settings => {
                this.state.gstRate = parseFloat(settings.gst_rate || 18.0);
                const gstInput = document.getElementById('settings-gst-rate');
                if (gstInput) {
                    gstInput.value = this.state.gstRate;
                }
            });
    }
};
