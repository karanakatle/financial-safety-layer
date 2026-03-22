package com.arthamantri.android.usage

import android.content.Context
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.core.DebugObservability
import com.arthamantri.android.core.StructuredMessageSignals
import com.arthamantri.android.repo.LiteracyRepository

enum class PaymentAppSetupState(val wireValue: String) {
    IDLE("idle"),
    UPI_REGISTRATION_STARTED("upi_registration_started"),
    PHONE_VERIFICATION("phone_verification"),
    BANK_ACCOUNT_FETCH("bank_account_fetch"),
    UPI_PIN_SETUP("upi_pin_setup"),
    REGISTRATION_SUCCESS("registration_success"),
    PAYMENT_READY("payment_ready"),
    ;

    companion object {
        fun fromWireValue(value: String?): PaymentAppSetupState =
            entries.firstOrNull { it.wireValue == value } ?: IDLE
    }
}

fun PaymentAppSetupState.isActiveOnboardingState(): Boolean = this in setOf(
    PaymentAppSetupState.UPI_REGISTRATION_STARTED,
    PaymentAppSetupState.PHONE_VERIFICATION,
    PaymentAppSetupState.BANK_ACCOUNT_FETCH,
    PaymentAppSetupState.UPI_PIN_SETUP,
    PaymentAppSetupState.REGISTRATION_SUCCESS,
)

enum class SetupStateSignal(val wireValue: String) {
    APP_OPEN("app_open"),
    PHONE_VERIFICATION("phone_verification"),
    BANK_ACCOUNT_FETCH("bank_account_fetch"),
    UPI_PIN_SETUP("upi_pin_setup"),
    REGISTRATION_SUCCESS("registration_success"),
    PAYMENT_SIGNAL("payment_signal"),
    ;
}

data class SetupStateInput(
    val signal: SetupStateSignal,
    val sourceApp: String? = null,
    val targetApp: String? = null,
    val nowMs: Long,
)

data class PersistedSetupState(
    val stateValue: String,
    val sourceApp: String?,
    val updatedAtMs: Long,
)

data class PaymentAppSetupSnapshot(
    val state: PaymentAppSetupState = PaymentAppSetupState.IDLE,
    val sourceApp: String? = null,
    val updatedAtMs: Long = 0L,
) {
    fun toPersistedValues(): PersistedSetupState = PersistedSetupState(
        stateValue = state.wireValue,
        sourceApp = sourceApp,
        updatedAtMs = updatedAtMs,
    )

    companion object {
        fun fromPersistedValues(
            stateValue: String?,
            sourceApp: String?,
            updatedAtMs: Long,
        ): PaymentAppSetupSnapshot = PaymentAppSetupSnapshot(
            state = PaymentAppSetupState.fromWireValue(stateValue),
            sourceApp = sourceApp,
            updatedAtMs = updatedAtMs,
        )
    }
}

data class SetupStateTransition(
    val previous: PaymentAppSetupSnapshot,
    val current: PaymentAppSetupSnapshot,
    val changed: Boolean,
    val expiredReset: Boolean,
    val signal: SetupStateSignal,
)

class DeterministicPaymentAppSetupStateMachine(
    private val setupExpiryMs: Long = 10 * 60 * 1000L,
    private val successExpiryMs: Long = 2 * 60 * 1000L,
) {
    fun transition(
        current: PaymentAppSetupSnapshot?,
        input: SetupStateInput,
    ): SetupStateTransition {
        val previous = current ?: PaymentAppSetupSnapshot()
        val expiredReset = isExpired(previous, input.nowMs)
        val baseline = if (expiredReset) {
            PaymentAppSetupSnapshot(updatedAtMs = input.nowMs)
        } else {
            previous
        }
        val nextState = nextStateFor(
            current = baseline.state,
            signal = input.signal,
        )
        val nextSnapshot = if (nextState == baseline.state) {
            baseline
        } else {
            PaymentAppSetupSnapshot(
                state = nextState,
                sourceApp = input.targetApp ?: baseline.sourceApp ?: input.sourceApp,
                updatedAtMs = input.nowMs,
            )
        }
        return SetupStateTransition(
            previous = previous,
            current = nextSnapshot,
            changed = nextSnapshot != previous,
            expiredReset = expiredReset,
            signal = input.signal,
        )
    }

    private fun isExpired(
        snapshot: PaymentAppSetupSnapshot,
        nowMs: Long,
    ): Boolean {
        if (snapshot.state == PaymentAppSetupState.IDLE) {
            return false
        }
        if (snapshot.updatedAtMs <= 0L) {
            return true
        }
        val expiryMs = when (snapshot.state) {
            PaymentAppSetupState.REGISTRATION_SUCCESS,
            PaymentAppSetupState.PAYMENT_READY,
            -> successExpiryMs
            else -> setupExpiryMs
        }
        return nowMs - snapshot.updatedAtMs > expiryMs
    }

    private fun nextStateFor(
        current: PaymentAppSetupState,
        signal: SetupStateSignal,
    ): PaymentAppSetupState = when (signal) {
        SetupStateSignal.APP_OPEN -> when (current) {
            PaymentAppSetupState.IDLE -> PaymentAppSetupState.UPI_REGISTRATION_STARTED
            PaymentAppSetupState.REGISTRATION_SUCCESS -> PaymentAppSetupState.PAYMENT_READY
            else -> current
        }
        SetupStateSignal.PHONE_VERIFICATION -> PaymentAppSetupState.PHONE_VERIFICATION
        SetupStateSignal.BANK_ACCOUNT_FETCH -> PaymentAppSetupState.BANK_ACCOUNT_FETCH
        SetupStateSignal.UPI_PIN_SETUP -> PaymentAppSetupState.UPI_PIN_SETUP
        SetupStateSignal.REGISTRATION_SUCCESS -> PaymentAppSetupState.REGISTRATION_SUCCESS
        SetupStateSignal.PAYMENT_SIGNAL -> PaymentAppSetupState.PAYMENT_READY
    }
}

object PaymentAppSetupStateTracker {
    private val machine = DeterministicPaymentAppSetupStateMachine()

    fun currentSnapshot(context: Context): PaymentAppSetupSnapshot {
        val prefs = context.getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        return PaymentAppSetupSnapshot.fromPersistedValues(
            stateValue = prefs.getString(AppConstants.Prefs.KEY_PAYMENT_APP_SETUP_STATE, null),
            sourceApp = prefs.getString(AppConstants.Prefs.KEY_PAYMENT_APP_SETUP_SOURCE_APP, null),
            updatedAtMs = prefs.getLong(AppConstants.Prefs.KEY_PAYMENT_APP_SETUP_UPDATED_AT_MS, 0L),
        )
    }

    suspend fun onAppOpen(
        context: Context,
        sourceApp: String,
        targetApp: String,
        correlationId: String? = null,
        nowMs: Long = System.currentTimeMillis(),
    ): SetupStateTransition = applyTransition(
        context = context,
        input = SetupStateInput(
            signal = SetupStateSignal.APP_OPEN,
            sourceApp = sourceApp,
            targetApp = targetApp,
            nowMs = nowMs,
        ),
        correlationId = correlationId,
    )

    suspend fun onStructuredMessage(
        context: Context,
        sourceApp: String?,
        targetApp: String?,
        rawText: String,
        signals: StructuredMessageSignals,
        correlationId: String? = null,
        nowMs: Long = System.currentTimeMillis(),
    ): SetupStateTransition? {
        val signal = inferSignal(rawText = rawText, signals = signals) ?: return null
        return applyTransition(
            context = context,
            input = SetupStateInput(
                signal = signal,
                sourceApp = sourceApp,
                targetApp = targetApp,
                nowMs = nowMs,
            ),
            correlationId = correlationId,
        )
    }

    private suspend fun applyTransition(
        context: Context,
        input: SetupStateInput,
        correlationId: String?,
    ): SetupStateTransition {
        val transition = machine.transition(
            current = currentSnapshot(context),
            input = input,
        )
        persist(context, transition.current)
        if (transition.changed || transition.expiredReset) {
            LiteracyRepository.submitContextEvent(
                context = context,
                eventType = AppConstants.ContextEvents.EVENT_SETUP_STATE_TRANSITION,
                sourceApp = input.sourceApp,
                targetApp = input.targetApp,
                correlationId = correlationId,
                classification = AppConstants.ContextEvents.CLASSIFICATION_OBSERVED,
                setupState = transition.current.state.wireValue,
                messageFamily = "setup_state",
                metadata = mapOf(
                    "previous_state" to transition.previous.state.wireValue,
                    "current_state" to transition.current.state.wireValue,
                    "transition_signal" to input.signal.wireValue,
                    "expired_reset" to transition.expiredReset.toString(),
                ),
            )
            DebugObservability.trace(
                context = context,
                tag = AppConstants.LogTags.DEBUG_OBSERVABILITY,
                event = "setup_state_transition",
                fields = mapOf(
                    "previous_state" to transition.previous.state.wireValue,
                    "current_state" to transition.current.state.wireValue,
                    "signal" to input.signal.wireValue,
                    "source_app" to input.sourceApp,
                    "target_app" to input.targetApp,
                    "expired_reset" to transition.expiredReset.toString(),
                    "correlation_id" to correlationId,
                ),
            )
        }
        return transition
    }

    private fun persist(
        context: Context,
        snapshot: PaymentAppSetupSnapshot,
    ) {
        val prefs = context.getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        prefs.edit()
            .putString(AppConstants.Prefs.KEY_PAYMENT_APP_SETUP_STATE, snapshot.state.wireValue)
            .putString(AppConstants.Prefs.KEY_PAYMENT_APP_SETUP_SOURCE_APP, snapshot.sourceApp)
            .putLong(AppConstants.Prefs.KEY_PAYMENT_APP_SETUP_UPDATED_AT_MS, snapshot.updatedAtMs)
            .apply()
    }

    private fun inferSignal(
        rawText: String,
        signals: StructuredMessageSignals,
    ): SetupStateSignal? {
        val normalized = signals.normalizedText
        return when {
            hasPhrase(normalized, "set upi pin") -> SetupStateSignal.UPI_PIN_SETUP
            hasPhrase(normalized, "link bank account") ||
                (hasPhrase(normalized, "bank account") && hasAnyPhrase(normalized, "fetch", "fetched", "linked", "link")) ->
                SetupStateSignal.BANK_ACCOUNT_FETCH
            hasPhrase(normalized, "successfully registered") ||
                hasPhrase(normalized, "registered your") ||
                (hasPhrase(normalized, "current device") && hasPhrase(normalized, "registered")) ->
                SetupStateSignal.REGISTRATION_SUCCESS
            signals.isOtpVerification ||
                hasPhrase(normalized, "verify mobile number") ||
                hasPhrase(normalized, "verification code") ||
                hasPhrase(normalized, "mobile verification") ->
                SetupStateSignal.PHONE_VERIFICATION
            signals.hasStrongPaymentSignal || rawText.contains("upi://pay", ignoreCase = true) ->
                SetupStateSignal.PAYMENT_SIGNAL
            else -> null
        }
    }

    private fun hasPhrase(normalized: String, phrase: String): Boolean =
        normalized.contains(" ${phrase.lowercase()} ")

    private fun hasAnyPhrase(normalized: String, vararg phrases: String): Boolean =
        phrases.any { hasPhrase(normalized, it) }
}
