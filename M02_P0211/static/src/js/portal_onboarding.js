(function() {
    'use strict';
    document.addEventListener('DOMContentLoaded', function() {
        const form = document.querySelector('.o_portal_onboarding_form');
        if (!form) return;

        // Image Preview Logic
        const fileInputs = form.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            input.addEventListener('change', function(e) {
                const file = e.target.files[0];
                const previewImg = e.target.parentElement.querySelector('.js_image_preview');
                
                if (file && !file.type.startsWith('image/')) {
                    alert('INVALID FILE TYPE: Please select an image file (PNG, JPG, JPEG). PDF files are not allowed.');
                    e.target.value = ''; // Clear input
                    if (previewImg) previewImg.classList.add('d-none');
                    return;
                }

                if (previewImg) {
                    if (file && file.type.startsWith('image/')) {
                        const reader = new FileReader();
                        reader.onload = function(event) {
                            previewImg.src = event.target.result;
                            previewImg.classList.remove('d-none');
                        };
                        reader.readAsDataURL(file);
                    } else {
                        previewImg.classList.add('d-none');
                    }
                }
            });
        });

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        // 1. Prepare Data from DOM
        const contractType = form.dataset.contractType || 'parttime';
        const existingFiles = {
            x_psm_0211_id_card_front: form.dataset.existingIdFront || '',
            x_psm_0211_id_card_back: form.dataset.existingIdBack || '',
            x_psm_0211_curriculum_vitae: form.dataset.existingCv || '',
            x_psm_0211_health_certificate: form.dataset.existingHealth || '',
            x_psm_0211_passport_photo: form.dataset.existingPhoto || ''
        };

        const inputs = {
            x_psm_0211_id_card_front: form.querySelector('input[name="x_psm_0211_id_card_front"]'),
            x_psm_0211_id_card_back: form.querySelector('input[name="x_psm_0211_id_card_back"]'),
            x_psm_0211_curriculum_vitae: form.querySelector('input[name="x_psm_0211_curriculum_vitae"]'),
            x_psm_0211_health_certificate: form.querySelector('input[name="x_psm_0211_health_certificate"]'),
            x_psm_0211_passport_photo: form.querySelector('input[name="x_psm_0211_passport_photo"]'),
            x_psm_0211_social_insurance: form.querySelector('input[name="x_psm_0211_social_insurance"]'),
            x_psm_0211_driving_license: form.querySelector('input[name="x_psm_0211_driving_license"]'),
            x_psm_0211_professional_certificate: form.querySelector('input[name="x_psm_0211_professional_certificate"]')
        };

        let missing = [];
        let summary = [];
        const partnerId = form.dataset.partnerId;
        
        // 2. Internal function to check status
        const checkField = (name, label, isMandatory) => {
            const inputElement = inputs[name];
            const hasExisting = existingFiles[name] || false;
            const hasNew = inputElement && inputElement.files.length > 0;
            const hasFile = hasNew || hasExisting;
            
            let imageHtml = '';
            if (hasFile) {
                let src = '';
                if (hasNew) {
                    // Get src from the live preview tag in the form
                    const pImg = inputElement.parentElement.querySelector('.js_image_preview');
                    src = pImg ? pImg.src : '';
                } else {
                    // URL to Odoo binary content
                    src = `/web/content?model=res.partner&id=${partnerId}&field=${name}`;
                }
                imageHtml = `<img src="${src}" class="img-thumbnail bg-white me-2" style="width: 45px; height: 45px; object-fit: cover;"/>`;
            } else {
                imageHtml = `<div class="bg-light me-2 border d-flex align-items-center justify-content-center" style="width: 45px; height: 45px; font-size: 10px; color: #ccc;">EMPTY</div>`;
            }

            if (isMandatory && !hasFile) {
                missing.push(label);
                summary.push(`
                    <div class="d-flex align-items-center mb-2 p-1 border rounded" style="background-color: #fff1f2; border-color: #fecaca !important;">
                        <span class="me-2 text-danger fw-bold">✘</span>
                        ${imageHtml}
                        <div class="small fw-bold text-danger">${label}: MISSING</div>
                    </div>
                `);
            } else if (hasFile) {
                summary.push(`
                    <div class="d-flex align-items-center mb-2 p-1 border rounded bg-white">
                        <span class="me-2 text-success fw-bold">✔</span>
                        ${imageHtml}
                        <div class="small text-dark">${label}</div>
                    </div>
                `);
            } else {
                summary.push(`
                    <div class="d-flex align-items-center mb-2 p-1 border rounded bg-light opacity-75">
                        <span class="me-2 text-muted fw-bold">○</span>
                        ${imageHtml}
                        <div class="small text-muted">${label}: NOT PROVIDED</div>
                    </div>
                `);
            }
        };

        // 3. Perform Checks
        checkField('x_psm_0211_id_card_front', 'Identity Card (Front Side)', true);
        checkField('x_psm_0211_id_card_back', 'Identity Card (Back Side)', true);
        checkField('x_psm_0211_curriculum_vitae', 'Personal History', true);
        checkField('x_psm_0211_health_certificate', 'Health Certificate', true);
        
        if (contractType === 'fulltime') {
           checkField('x_psm_0211_passport_photo', 'Passport Photo (3x4)', true);
           
           // Add additional optional docs only for FT in summary
           summary.push('<hr class="my-2 border-dashed"/>');
           checkField('x_psm_0211_social_insurance', 'Social Insurance Book', false);
           checkField('x_psm_0211_driving_license', 'Driving License', false);
           checkField('x_psm_0211_professional_certificate', 'Academic Degree', false);
        }

        // 4. Update Modal UI
        const summaryDiv = document.getElementById('modal-summary-content');
        const confirmBtn = document.getElementById('btn-final-confirm');
        
        if (!summaryDiv || !confirmBtn) return;

        if (missing.length > 0) {
            summaryDiv.innerHTML = `
                <div class="alert alert-danger py-2 small fw-bold mb-3">MANDATORY DOCUMENTS MISSING!</div>
                ${summary.join('')}
                <div class="mt-3 text-muted small italic">Please provide all mandatory documents marked with ✘ before confirming.</div>
            `;
            confirmBtn.classList.add('d-none');
        } else {
            summaryDiv.innerHTML = `
                <div class="alert alert-success py-2 small fw-bold mb-3">ALL MANDATORY DOCUMENTS READY.</div>
                <div class="mb-2 small text-muted text-uppercase fw-bold">Review Selected Documents:</div>
                <div class="summary-list">
                    ${summary.join('')}
                </div>
                <div class="mt-3 text-dark small italic fw-bold p-2 bg-light border-start border-3 border-danger">
                    Ready to submit? Once confirmed, you cannot undo this action.
                </div>
            `;
            confirmBtn.classList.remove('d-none');
        }

        // 5. Show Modal
        const modalElement = document.getElementById('submitConfirmModal');
        if (modalElement) {
            const bootstrap = window.bootstrap || window.odoo && window.odoo.bootstrap;
            if (bootstrap && bootstrap.Modal) {
                const modal = new bootstrap.Modal(modalElement);
                modal.show();

                confirmBtn.onclick = function() {
                    confirmBtn.disabled = true;
                    confirmBtn.innerHTML = 'Submitting...';
                    form.submit();
                };
            } else if (typeof $ !== 'undefined' && $.fn.modal) {
                // Fallback to jQuery if legacy
                $(modalElement).modal('show');
                confirmBtn.onclick = function() {
                    confirmBtn.disabled = true;
                    confirmBtn.innerHTML = 'Submitting...';
                    form.submit();
                };
            } else {
                // Last resort: standard submit with alert
                if (confirm('Ready to submit documents?')) {
                    form.submit();
                }
            }
        }
    });

    // --- NEW: Document Preview Lightbox Logic ---
    const imagePreviewModal = document.getElementById('imagePreviewModal');
    if (imagePreviewModal) {
        imagePreviewModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget; // Element that triggered the modal
            const src = button.getAttribute('data-src');
            const title = button.getAttribute('data-title');
            
            const modalImage = imagePreviewModal.querySelector('#modal-preview-image');
            const modalTitle = imagePreviewModal.querySelector('#modal-image-title');
            
            if (modalImage) modalImage.src = src;
            if (modalTitle) modalTitle.textContent = title || 'DOCUMENT PREVIEW';
        });
    }
});
})();
