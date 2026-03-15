package com.arthamantri.android.sms

import com.arthamantri.android.core.AppConstants
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class SmsParserTest {
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
    fun `parser detects income signal from credit sms`() {
        val parsed = SmsParser.parseSignal(
            sender = "VK-HDFCBK",
            message = "Rs 12000 credited to your account as salary",
        )

        assertNotNull(parsed)
        assertEquals(AppConstants.Domain.SMS_SIGNAL_INCOME, parsed?.signalType)
        assertEquals(AppConstants.Domain.SMS_SIGNAL_CONFIRMED, parsed?.confidence)
        assertEquals(12000.0, parsed?.amount)
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
}
