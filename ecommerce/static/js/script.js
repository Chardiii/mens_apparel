/* ── Mode S7vn — script.js ─────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', async () => {

    // ── 1. Auto-show server-side toasts ──────────────────────────
    document.querySelectorAll('.toast').forEach(el => {
        new bootstrap.Toast(el, { delay: 4000 }).show()
    })


    // ── 2. JS Toast helper ────────────────────────────────────────
    window.showToast = function(message, type = 'info') {
        const icons = { success: '✅', danger: '❌', warning: '⚠️', info: 'ℹ️' }
        const id = `toast-${Date.now()}`
        const html = `
        <div id="${id}" class="toast align-items-center text-white border-0 toast-${type} show"
             role="alert" data-bs-autohide="true" data-bs-delay="4000">
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center gap-2">
                    <span>${icons[type] || 'ℹ️'}</span> ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto"
                        data-bs-dismiss="toast"></button>
            </div>
        </div>`
        const container = document.getElementById('js-toast-container')
        container.insertAdjacentHTML('beforeend', html)
        const toastEl = document.getElementById(id)
        new bootstrap.Toast(toastEl, { delay: 4000 }).show()
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove())
    }


    // ── 3. Wishlist AJAX toggle ───────────────────────────────────
    document.querySelectorAll('.wishlist-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const productId = btn.dataset.productId
            try {
                const res = await fetch(`/wishlist/toggle/${productId}`, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                })
                if (res.status === 403) {
                    showToast('Login as a buyer to use the wishlist.', 'warning')
                    return
                }
                const data = await res.json()
                const added = data.status === 'added'

                btn.dataset.wishlisted = added ? 'true' : 'false'

                // Update button text depending on context
                if (btn.textContent.trim().length > 2) {
                    btn.textContent = added ? '♥ Wishlisted' : '♡ Add to Wishlist'
                } else {
                    btn.textContent = added ? '♥' : '♡'
                }
                btn.classList.toggle('btn-danger', added)
                btn.classList.toggle('btn-outline-danger', !added)

                showToast(data.message, added ? 'success' : 'info')

                // Remove card from wishlist page if we're on it
                const card = document.getElementById(`wishlist-card-${productId}`)
                if (card && !added) card.remove()

            } catch {
                showToast('Something went wrong. Try again.', 'danger')
            }
        })
    })


    // ── 4. Form validation ────────────────────────────────────────
    document.querySelectorAll('form[data-validate]').forEach(form => {
        form.addEventListener('submit', e => {
            let valid = true

            // Required text/select/textarea fields
            form.querySelectorAll('[required]').forEach(field => {
                const empty = field.value.trim() === ''
                field.classList.toggle('is-invalid', empty)
                if (empty) valid = false
            })

            // Required file inputs
            form.querySelectorAll('input[type="file"][required]').forEach(field => {
                const empty = field.files.length === 0
                field.classList.toggle('is-invalid', empty)
                if (empty) valid = false
            })

            // File size check (max 4MB per file)
            form.querySelectorAll('input[type="file"]').forEach(field => {
                Array.from(field.files).forEach(file => {
                    if (file.size > 4 * 1024 * 1024) {
                        field.classList.add('is-invalid')
                        showToast(`"${file.name}" exceeds 4MB limit.`, 'warning')
                        valid = false
                    }
                })
            })

            // Password match check
            const pw  = form.querySelector('[name="password"]')
            const cpw = form.querySelector('[name="confirm_password"]')
            if (pw && cpw && pw.value && cpw.value && pw.value !== cpw.value) {
                cpw.classList.add('is-invalid')
                showToast('Passwords do not match.', 'danger')
                valid = false
            }

            if (!valid) {
                e.preventDefault()
                showToast('Please fill in all required fields.', 'danger')
            }
        })

        // Clear invalid state on input
        form.querySelectorAll('.form-control, .form-select').forEach(field => {
            field.addEventListener('input', () => field.classList.remove('is-invalid'))
        })
    })


    // ── 5. Password strength meter + requirements checklist ──────────────
    const pwField = document.getElementById('password-field')
    const strengthBar  = document.getElementById('pw-strength-bar')
    const strengthText = document.getElementById('pw-strength-text')

    if (pwField && strengthBar) {
        pwField.addEventListener('input', () => {
            const val = pwField.value
            let score = 0
            if (val.length >= 8)              score++
            if (val.length >= 12)             score++
            if (/[A-Z]/.test(val))            score++
            if (/[0-9]/.test(val))            score++
            if (/[^A-Za-z0-9]/.test(val))     score++

            const levels = [
                { label: '',           color: '',           width: '0%'   },
                { label: 'Very Weak',  color: 'bg-danger',  width: '20%'  },
                { label: 'Weak',       color: 'bg-warning', width: '40%'  },
                { label: 'Fair',       color: 'bg-info',    width: '60%'  },
                { label: 'Strong',     color: 'bg-primary', width: '80%'  },
                { label: 'Very Strong',color: 'bg-success', width: '100%' },
            ]
            const level = levels[score] || levels[0]
            strengthBar.style.width = level.width
            strengthBar.className   = `progress-bar ${level.color}`
            if (strengthText) strengthText.textContent = level.label

            // Live requirements checklist
            const mark = (id, ok) => {
                const el = document.getElementById(id)
                if (!el) return
                el.style.color     = ok ? '#198754' : ''
                el.style.fontWeight = ok ? 'bold' : ''
                el.textContent = el.textContent.replace(/^[\u2713\u2717] /, '')
                el.textContent = (ok ? '\u2713 ' : '\u2717 ') + el.textContent
            }
            mark('req-len',     val.length >= 8)
            mark('req-upper',   /[A-Z]/.test(val))
            mark('req-num',     /[0-9]/.test(val))
            mark('req-special', /[^A-Za-z0-9]/.test(val))
        })
    }


    // ── 6. Show / hide password toggle ───────────────────────────────
    document.querySelectorAll('.toggle-pw').forEach(btn => {
        btn.addEventListener('click', () => {
            const input = document.getElementById(btn.dataset.target)
            if (!input) return
            const show = input.type === 'password'
            input.type  = show ? 'text' : 'password'
            btn.textContent = show ? '🙈' : '👁'
        })
    })


    // ── 7. PSGC cascading address dropdowns ─────────────────────────
    const PSGC = 'https://psgc.gitlab.io/api'

    const selRegion   = document.getElementById('psgc-region')
    const selProvince = document.getElementById('psgc-province')
    const selMuni     = document.getElementById('psgc-municipality')
    const selBrgy     = document.getElementById('psgc-barangay')

    if (selRegion) {
        const populate = async (sel, url, placeholder) => {
            sel.innerHTML = `<option value="">${placeholder}</option>`
            sel.disabled = true
            try {
                const data = await (await fetch(url)).json()
                const sorted = data.sort((a, b) => a.name.localeCompare(b.name))
                sorted.forEach(item => {
                    const opt = document.createElement('option')
                    opt.value = item.name
                    opt.dataset.code = item.code
                    opt.textContent  = item.name
                    sel.appendChild(opt)
                })
                sel.disabled = false
            } catch { sel.disabled = false }
        }

        const resetBelow = (...sels) => sels.forEach(s => {
            s.innerHTML = `<option value="">— Select —</option>`
            s.disabled = true
        })

        const getCode = sel => sel.options[sel.selectedIndex]?.dataset.code

        // Load regions on page load
        await populate(selRegion, `${PSGC}/regions/`, '— Select Region —')

        selRegion.addEventListener('change', async () => {
            resetBelow(selProvince, selMuni, selBrgy)
            if (!selRegion.value) return
            const code = getCode(selRegion)
            await populate(selProvince, `${PSGC}/regions/${code}/provinces/`, '— Select Province —')
        })

        selProvince.addEventListener('change', async () => {
            resetBelow(selMuni, selBrgy)
            if (!selProvince.value) return
            const code = getCode(selProvince)
            await populate(selMuni, `${PSGC}/provinces/${code}/cities-municipalities/`, '— Select City / Municipality —')
        })

        selMuni.addEventListener('change', async () => {
            resetBelow(selBrgy)
            if (!selMuni.value) return
            const code = getCode(selMuni)
            await populate(selBrgy, `${PSGC}/cities-municipalities/${code}/barangays/`, '— Select Barangay —')
        })

        // Pre-fill saved values (edit profile)
        const prefill = window._psgcPrefill
        if (prefill && prefill.region) {
            // Wait for regions to load then cascade
            const waitAndSelect = (sel, value, cb) => {
                const interval = setInterval(() => {
                    const opt = Array.from(sel.options).find(o => o.value === value)
                    if (opt) {
                        sel.value = value
                        clearInterval(interval)
                        if (cb) cb()
                    }
                }, 100)
            }

            waitAndSelect(selRegion, prefill.region, async () => {
                const rCode = getCode(selRegion)
                await populate(selProvince, `${PSGC}/regions/${rCode}/provinces/`, '— Select Province —')
                if (!prefill.province) return
                waitAndSelect(selProvince, prefill.province, async () => {
                    const pCode = getCode(selProvince)
                    await populate(selMuni, `${PSGC}/provinces/${pCode}/cities-municipalities/`, '— Select City / Municipality —')
                    if (!prefill.municipality) return
                    waitAndSelect(selMuni, prefill.municipality, async () => {
                        const mCode = getCode(selMuni)
                        await populate(selBrgy, `${PSGC}/cities-municipalities/${mCode}/barangays/`, '— Select Barangay —')
                        if (!prefill.barangay) return
                        waitAndSelect(selBrgy, prefill.barangay, null)
                    })
                })
            })
        }
    }


    // ── 8. Live search suggestions ────────────────────────────────
    const searchInput   = document.getElementById('search-input')
    const suggestionBox = document.getElementById('search-suggestions')

    if (searchInput && suggestionBox) {
        let debounceTimer

        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer)
            const q = searchInput.value.trim()

            if (q.length < 2) {
                suggestionBox.style.display = 'none'
                suggestionBox.innerHTML = ''
                return
            }

            debounceTimer = setTimeout(async () => {
                try {
                    const res  = await fetch(`/products/search-suggestions?q=${encodeURIComponent(q)}`)
                    const data = await res.json()

                    if (!data.length) {
                        suggestionBox.style.display = 'none'
                        return
                    }

                    suggestionBox.innerHTML = data.map(p => `
                        <li class="list-group-item list-group-item-action suggestion-item"
                            data-name="${p.name}" style="cursor:pointer;">
                            <div class="d-flex justify-content-between align-items-center">
                                <span>${p.name}</span>
                                <small class="text-muted">₱${parseFloat(p.price).toFixed(2)}</small>
                            </div>
                            ${p.category ? `<small class="text-muted">${p.category}</small>` : ''}
                        </li>`).join('')

                    suggestionBox.style.display = 'block'

                    // Click suggestion → fill input and submit
                    suggestionBox.querySelectorAll('.suggestion-item').forEach(item => {
                        item.addEventListener('click', () => {
                            searchInput.value = item.dataset.name
                            suggestionBox.style.display = 'none'
                            searchInput.closest('form').submit()
                        })
                    })
                } catch {
                    suggestionBox.style.display = 'none'
                }
            }, 280)
        })

        // Hide suggestions on outside click
        document.addEventListener('click', e => {
            if (!searchInput.contains(e.target) && !suggestionBox.contains(e.target)) {
                suggestionBox.style.display = 'none'
            }
        })

        // Keyboard navigation
        searchInput.addEventListener('keydown', e => {
            const items = suggestionBox.querySelectorAll('.suggestion-item')
            const active = suggestionBox.querySelector('.active')
            if (!items.length) return

            if (e.key === 'ArrowDown') {
                e.preventDefault()
                const next = active ? active.nextElementSibling : items[0]
                if (active) active.classList.remove('active')
                if (next) next.classList.add('active')
            } else if (e.key === 'ArrowUp') {
                e.preventDefault()
                const prev = active ? active.previousElementSibling : items[items.length - 1]
                if (active) active.classList.remove('active')
                if (prev) prev.classList.add('active')
            } else if (e.key === 'Enter' && active) {
                e.preventDefault()
                searchInput.value = active.dataset.name
                suggestionBox.style.display = 'none'
                searchInput.closest('form').submit()
            } else if (e.key === 'Escape') {
                suggestionBox.style.display = 'none'
            }
        })
    }

})
