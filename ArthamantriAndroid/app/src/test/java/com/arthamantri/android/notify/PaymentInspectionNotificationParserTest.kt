package com.arthamantri.android.notify

import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.usage.PaymentAppSetupState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class PaymentInspectionNotificationParserTest {
    private data class OnboardingFixture(
        val packageName: String,
        val appName: String,
    )

    private val onboardingApps = listOf(
        OnboardingFixture("com.phonepe.app", "PhonePe"),
        OnboardingFixture("com.google.android.apps.nbu.paisa.user", "Google Pay"),
        OnboardingFixture("net.one97.paytm", "Paytm"),
    )

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

    @Test
    fun `parser suppresses ambiguous upi handle during active setup`() {
        val signal = PaymentInspectionNotificationParser.parse(
            packageName = "com.phonepe.app",
            appName = "PhonePe",
            title = "PhonePe setup",
            text = "Continue device verification with helper@upi",
            bigText = "",
            isUpiPackage = true,
            setupState = PaymentAppSetupState.PHONE_VERIFICATION,
        )

        assertNull(signal)
    }

    @Test
    fun `parser keeps explicit collect request visible during active setup`() {
        val signal = PaymentInspectionNotificationParser.parse(
            packageName = "com.phonepe.app",
            appName = "PhonePe",
            title = "Payment request from Ravi",
            text = "Approve collect request of Rs 2500",
            bigText = "Collect request from ravi@upi",
            isUpiPackage = true,
            setupState = PaymentAppSetupState.PHONE_VERIFICATION,
        )

        assertNotNull(signal)
        assertEquals(AppConstants.PaymentInspection.REQUEST_KIND_COLLECT, signal?.requestKind)
    }

    @Test
    fun `parser suppresses registration success fixtures for all onboarding apps`() {
        onboardingApps.forEach { fixture ->
            val signal = PaymentInspectionNotificationParser.parse(
                packageName = fixture.packageName,
                appName = fixture.appName,
                title = fixture.appName,
                text = "Use ${fixture.appName} on your current device!",
                bigText = "You have successfully registered your ${fixture.appName} account.",
                isUpiPackage = true,
                setupState = PaymentAppSetupState.REGISTRATION_SUCCESS,
            )

            assertNull("${fixture.appName} registration success should stay silent", signal)
        }
    }

    @Test
    fun `parser suppresses phone verification fixtures for all onboarding apps`() {
        onboardingApps.forEach { fixture ->
            val signal = PaymentInspectionNotificationParser.parse(
                packageName = fixture.packageName,
                appName = fixture.appName,
                title = "${fixture.appName} verification",
                text = "Verify mobile number to continue setup",
                bigText = "Your verification code is 456789 for ${fixture.appName}",
                isUpiPackage = true,
                setupState = PaymentAppSetupState.PHONE_VERIFICATION,
            )

            assertNull("${fixture.appName} phone verification should stay silent", signal)
        }
    }

    @Test
    fun `parser suppresses bank fetch fixtures for all onboarding apps`() {
        onboardingApps.forEach { fixture ->
            val signal = PaymentInspectionNotificationParser.parse(
                packageName = fixture.packageName,
                appName = fixture.appName,
                title = "${fixture.appName} setup",
                text = "Link bank account to continue",
                bigText = "Bank account fetch in progress for ${fixture.appName}",
                isUpiPackage = true,
                setupState = PaymentAppSetupState.BANK_ACCOUNT_FETCH,
            )

            assertNull("${fixture.appName} bank fetch should stay silent", signal)
        }
    }

    @Test
    fun `parser suppresses pin setup fixtures for all onboarding apps`() {
        onboardingApps.forEach { fixture ->
            val signal = PaymentInspectionNotificationParser.parse(
                packageName = fixture.packageName,
                appName = fixture.appName,
                title = "${fixture.appName} setup",
                text = "Set UPI PIN to finish setup",
                bigText = "Complete device verification before you set UPI PIN",
                isUpiPackage = true,
                setupState = PaymentAppSetupState.UPI_PIN_SETUP,
            )

            assertNull("${fixture.appName} PIN setup should stay silent", signal)
        }
    }

    @Test
    fun `parser keeps explicit collect fixtures visible for all onboarding apps`() {
        onboardingApps.forEach { fixture ->
            val signal = PaymentInspectionNotificationParser.parse(
                packageName = fixture.packageName,
                appName = fixture.appName,
                title = "Payment request from Ravi",
                text = "Approve collect request of Rs 2500",
                bigText = "Collect request from ravi@upi",
                isUpiPackage = true,
                setupState = PaymentAppSetupState.BANK_ACCOUNT_FETCH,
            )

            assertNotNull("${fixture.appName} explicit collect must remain visible", signal)
            assertEquals(AppConstants.PaymentInspection.REQUEST_KIND_COLLECT, signal?.requestKind)
        }
    }
}
