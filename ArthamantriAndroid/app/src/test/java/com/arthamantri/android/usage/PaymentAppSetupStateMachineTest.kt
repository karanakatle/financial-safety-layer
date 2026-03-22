package com.arthamantri.android.usage

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PaymentAppSetupStateMachineTest {
    private val machine = DeterministicPaymentAppSetupStateMachine(
        setupExpiryMs = 60_000L,
        successExpiryMs = 30_000L,
    )

    @Test
    fun `app open starts setup flow from idle`() {
        val transition = machine.transition(
            current = null,
            input = SetupStateInput(
                signal = SetupStateSignal.APP_OPEN,
                sourceApp = "com.phonepe.app",
                targetApp = "PhonePe",
                nowMs = 1_000L,
            ),
        )

        assertTrue(transition.changed)
        assertEquals(PaymentAppSetupState.IDLE, transition.previous.state)
        assertEquals(PaymentAppSetupState.UPI_REGISTRATION_STARTED, transition.current.state)
    }

    @Test
    fun `setup flow advances deterministically through registration states`() {
        val opened = machine.transition(
            current = null,
            input = SetupStateInput(
                signal = SetupStateSignal.APP_OPEN,
                sourceApp = "com.phonepe.app",
                targetApp = "PhonePe",
                nowMs = 1_000L,
            ),
        ).current
        val phoneVerification = machine.transition(
            current = opened,
            input = SetupStateInput(
                signal = SetupStateSignal.PHONE_VERIFICATION,
                sourceApp = "com.phonepe.app",
                targetApp = "PhonePe",
                nowMs = 2_000L,
            ),
        ).current
        val bankFetch = machine.transition(
            current = phoneVerification,
            input = SetupStateInput(
                signal = SetupStateSignal.BANK_ACCOUNT_FETCH,
                sourceApp = "com.phonepe.app",
                targetApp = "PhonePe",
                nowMs = 3_000L,
            ),
        ).current
        val pinSetup = machine.transition(
            current = bankFetch,
            input = SetupStateInput(
                signal = SetupStateSignal.UPI_PIN_SETUP,
                sourceApp = "com.phonepe.app",
                targetApp = "PhonePe",
                nowMs = 4_000L,
            ),
        ).current
        val registrationSuccess = machine.transition(
            current = pinSetup,
            input = SetupStateInput(
                signal = SetupStateSignal.REGISTRATION_SUCCESS,
                sourceApp = "com.phonepe.app",
                targetApp = "PhonePe",
                nowMs = 5_000L,
            ),
        ).current
        val paymentReady = machine.transition(
            current = registrationSuccess,
            input = SetupStateInput(
                signal = SetupStateSignal.APP_OPEN,
                sourceApp = "com.phonepe.app",
                targetApp = "PhonePe",
                nowMs = 6_000L,
            ),
        )

        assertEquals(PaymentAppSetupState.PHONE_VERIFICATION, phoneVerification.state)
        assertEquals(PaymentAppSetupState.BANK_ACCOUNT_FETCH, bankFetch.state)
        assertEquals(PaymentAppSetupState.UPI_PIN_SETUP, pinSetup.state)
        assertEquals(PaymentAppSetupState.REGISTRATION_SUCCESS, registrationSuccess.state)
        assertEquals(PaymentAppSetupState.PAYMENT_READY, paymentReady.current.state)
        assertTrue(paymentReady.changed)
    }

    @Test
    fun `expired setup state resets before applying next transition`() {
        val stale = PaymentAppSetupSnapshot(
            state = PaymentAppSetupState.PHONE_VERIFICATION,
            sourceApp = "PhonePe",
            updatedAtMs = 0L,
        )

        val transition = machine.transition(
            current = stale,
            input = SetupStateInput(
                signal = SetupStateSignal.APP_OPEN,
                sourceApp = "com.phonepe.app",
                targetApp = "PhonePe",
                nowMs = 120_000L,
            ),
        )

        assertTrue(transition.expiredReset)
        assertEquals(PaymentAppSetupState.UPI_REGISTRATION_STARTED, transition.current.state)
    }

    @Test
    fun `snapshot can be restored from persisted values`() {
        val snapshot = PaymentAppSetupSnapshot(
            state = PaymentAppSetupState.BANK_ACCOUNT_FETCH,
            sourceApp = "PhonePe",
            updatedAtMs = 9_000L,
        )

        val persisted = snapshot.toPersistedValues()
        val restored = PaymentAppSetupSnapshot.fromPersistedValues(
            stateValue = persisted.stateValue,
            sourceApp = persisted.sourceApp,
            updatedAtMs = persisted.updatedAtMs,
        )

        assertEquals(snapshot, restored)
        assertFalse(
            PaymentAppSetupSnapshot.fromPersistedValues(
                stateValue = "unknown_state",
                sourceApp = "PhonePe",
                updatedAtMs = 1_000L,
            ).state != PaymentAppSetupState.IDLE
        )
    }
}
