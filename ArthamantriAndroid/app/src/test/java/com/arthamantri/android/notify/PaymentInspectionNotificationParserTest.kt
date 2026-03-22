package com.arthamantri.android.notify

import com.arthamantri.android.core.AppConstants
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class PaymentInspectionNotificationParserTest {
    @Test
    fun `parser extracts collect style notification context`() {
        val signal = PaymentInspectionNotificationParser.parse(
            packageName = "com.phonepe.app",
            appName = "PhonePe",
            title = "Payment request from Ravi",
            text = "Approve collect request of Rs 2500",
            bigText = "Collect request from ravi@upi",
            isUpiPackage = true,
        )

        assertNotNull(signal)
        assertEquals(AppConstants.PaymentInspection.REQUEST_KIND_COLLECT, signal?.requestKind)
        assertEquals(2500.0, signal?.amount)
        assertEquals("Payment request from Ravi", signal?.payeeLabel)
        assertEquals("ravi@upi", signal?.payeeHandle)
    }

    @Test
    fun `parser ignores generic upi notification without payment intent`() {
        val signal = PaymentInspectionNotificationParser.parse(
            packageName = "com.phonepe.app",
            appName = "PhonePe",
            title = "PhonePe",
            text = "UPI activity detected",
            bigText = "",
            isUpiPackage = true,
        )

        assertNull(signal)
    }

    @Test
    fun `parser ignores unrelated notification payloads`() {
        val signal = PaymentInspectionNotificationParser.parse(
            packageName = "com.example.other",
            appName = "Other",
            title = "Welcome",
            text = "Your weekly summary is ready",
            bigText = "",
            isUpiPackage = false,
        )

        assertNull(signal)
    }
}
