(function () {
    const planOptions = document.querySelectorAll('.payment-option-card');
    const planToggleInputs = document.querySelectorAll('input[name="payment_option"]');
    const partialSection = document.getElementById('partial-payment-section');
    const fullSection = document.getElementById('full-payment-section');
    const planTypeField = document.getElementById('id_plan_type');
    const installmentsWrapper = document.getElementById('installment-count-wrapper');
    const installmentsInput = document.getElementById('id_installment_count');
    const installmentsSummary = document.getElementById('installment-summary');
    const installmentsSummaryText = document.getElementById('installment-summary-text');
    const initialPaymentInput = document.getElementById('id_initial_payment_amount');
    const minDepositDisplay = document.getElementById('minimum-deposit-value');

    const totalAmountRaw = parseFloat(document.body.dataset.checkoutTotal || '0');
    const minDepositRaw = parseFloat(document.body.dataset.checkoutMinDeposit || '0');
    const totalAmount = Number.isNaN(totalAmountRaw) ? 0 : totalAmountRaw;
    const minDeposit = Number.isNaN(minDepositRaw) ? 0 : minDepositRaw;

    const toggleSections = () => {
        const selected = document.querySelector('input[name="payment_option"]:checked');
        const usePartial = selected && selected.value === 'partial';
        if (partialSection) partialSection.style.display = usePartial ? '' : 'none';
        if (fullSection) fullSection.classList.toggle('border-primary', !usePartial);
        planOptions.forEach(card => {
            const cardInput = card.querySelector('input[name="payment_option"]');
            card.classList.toggle('border-primary', cardInput?.checked);
            card.classList.toggle('shadow', cardInput?.checked);
        });
    };

    const updateInstallmentSummary = () => {
        if (!installmentsInput || !installmentsSummary) return;
        const count = parseInt(installmentsInput.value, 10);
        if (!count || count <= 0) {
            installmentsSummary.style.display = 'none';
            return;
        }
        const perInstallment = (totalAmount / count).toFixed(2);
        installmentsSummaryText.textContent = `${count} × $${perInstallment}`;
        installmentsSummary.style.display = '';
    };

    const ensureMinimumDeposit = () => {
        if (!initialPaymentInput) return;
        const current = parseFloat(initialPaymentInput.value || '0');
        if (current < minDeposit) {
            initialPaymentInput.value = minDeposit.toFixed(2);
        }
    };

    planOptions.forEach(card => {
        card.addEventListener('click', () => {
            const radio = card.querySelector('input[type="radio"]');
            if (radio) {
                radio.checked = true;
                toggleSections();
            }
        });
    });

    planToggleInputs.forEach(input => {
        input.addEventListener('change', toggleSections);
    });

    planTypeField?.addEventListener('change', () => {
        const showInstallments = planTypeField.value === 'installment';
        if (installmentsWrapper) {
            installmentsWrapper.style.display = showInstallments ? '' : 'none';
        }
        if (!showInstallments && installmentsSummary) {
            installmentsSummary.style.display = 'none';
        } else {
            updateInstallmentSummary();
        }
    });

    installmentsInput?.addEventListener('input', updateInstallmentSummary);
    initialPaymentInput?.addEventListener('blur', ensureMinimumDeposit);

    if (minDepositDisplay) {
        minDepositDisplay.textContent = minDeposit.toFixed(2);
    }

    ensureMinimumDeposit();
    toggleSections();
    updateInstallmentSummary();
})();
