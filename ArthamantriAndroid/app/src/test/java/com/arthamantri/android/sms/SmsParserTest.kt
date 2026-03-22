package com.arthamantri.android.sms

import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.usage.PaymentAppSetupState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class SmsParserTest {
    private data class SetupSmsFixture(
        val sender: String,
        val message: String,
        val setupState: PaymentAppSetupState,
    )

    @Test
    fun `parser detects expense signal from debit sms`() {
        val parsed = SmsParser.parseSignal(
            sender = "VK-HDFCBK",
            message = "INR 2500 debited via UPI to merchant",
        )

        assertNotNull(parsed)
        assertEquals(AppConstants.Domain.SMS_SIGNAL_EXPENSE, parsed?.signalType)
        assertEquals(AppConstants.Domain.SMS_SIGNAL_CONFIRMED, parsed?.confidence)
        assertEquals(2500.0, parsed?.amount)
        assertEquals(AppConstants.Domain.CATEGORY_UPI, parsed?.category)
    }

    @Test
    fun `parser suppresses benign income signal from credit sms`() {
        val parsed = SmsParser.parseSignal(
            sender = "VK-HDFCBK",
            message = "Rs 12000 credited to your account as salary",
        )

        assertNull(parsed)
    }

    @Test
    fun `parser keeps ambiguous amount sms as partial signal`() {
        val parsed = SmsParser.parseSignal(
            sender = "VK-HDFCBK",
            message = "Txn alert: INR 5000 on your account. Check bank app if this was expected.",
        )

        assertNotNull(parsed)
        assertEquals(AppConstants.Domain.SMS_SIGNAL_PARTIAL, parsed?.signalType)
        assertEquals(AppConstants.Domain.SMS_SIGNAL_PARTIAL_CONFIDENCE, parsed?.confidence)
        assertEquals(5000.0, parsed?.amount)
    }

    @Test
    fun `parser ignores non financial sms noise`() {
        val parsed = SmsParser.parseSignal(
            sender = "AD-STORE",
            message = "Big sale today. Buy one get one free.",
        )

        assertNull(parsed)
    }

    @Test
    fun `parser ignores wallet and voucher style promotional credits`() {
        val parsed = SmsParser.parseSignal(
            sender = "AD-MYNTRA",
            message = "Rs 1000 credited in your wallet as a gift voucher offer.",
        )

        assertNull(parsed)
    }

    @Test
    fun `parser ignores pay balance promotional credits`() {
        val parsed = SmsParser.parseSignal(
            sender = "AD-AMAZON",
            message = "Rs 500 added to your Amazon Pay balance as a promo offer.",
        )

        assertNull(parsed)
    }

    @Test
    fun `parser ignores reward points style non cash credits`() {
        val parsed = SmsParser.parseSignal(
            sender = "AD-STORE",
            message = "Rs 300 credited as reward points on your shopping account.",
        )

        assertNull(parsed)
    }

    @Test
    fun `parser downgrades debit copy with marketing disclaimer to partial`() {
        val parsed = SmsParser.parseSignal(
            sender = "VK-BANK",
            message = "Rs 900 debited from your account, but can be avoided if you do this thing.",
        )

        assertNotNull(parsed)
        assertEquals(AppConstants.Domain.SMS_SIGNAL_PARTIAL, parsed?.signalType)
        assertEquals(AppConstants.Domain.SMS_SIGNAL_PARTIAL_CONFIDENCE, parsed?.confidence)
        assertEquals(900.0, parsed?.amount)
    }

    @Test
    fun `parser suppresses partial upi setup sms when onboarding is active`() {
        val parsed = SmsParser.parseSignal(
            sender = "VM-PHONPE",
            message = "Txn alert: UPI account setup in progress for your bank profile.",
            setupState = PaymentAppSetupState.PHONE_VERIFICATION,
        )

        assertNull(parsed)
    }

    @Test
    fun `parser suppresses setup sms fixtures across onboarding phases`() {
        val fixtures = listOf(
            SetupSmsFixture(
                sender = "VM-PHONPE",
                message = "Your verification code is 245611. Verify mobile number to continue PhonePe setup.",
                setupState = PaymentAppSetupState.PHONE_VERIFICATION,
            ),
            SetupSmsFixture(
                sender = "VM-GPAY",
                message = "Link bank account to continue setup. Bank account fetch in progress for Google Pay.",
                setupState = PaymentAppSetupState.BANK_ACCOUNT_FETCH,
            ),
            SetupSmsFixture(
                sender = "VM-PAYTM",
                message = "Set UPI PIN to complete Paytm setup for your bank profile.",
                setupState = PaymentAppSetupState.UPI_PIN_SETUP,
            ),
        )

        fixtures.forEach { fixture ->
            val parsed = SmsParser.parseSignal(
                sender = fixture.sender,
                message = fixture.message,
                setupState = fixture.setupState,
            )

            assertNull("${fixture.sender} setup fixture should stay silent", parsed)
        }
    }
}
