package com.arthamantri.android

internal enum class OnboardingStep {
    LANGUAGE,
    PURPOSE_AND_CONSENT,
    MONEY_SETUP,
    PERMISSIONS,
    COMPLETE,
}

internal enum class HomePrimaryActionState {
    RESUME_SETUP,
    START_MONITORING,
}

internal enum class HomeStatusState {
    CHOOSE_LANGUAGE,
    REVIEW_CONSENT,
    SETUP_PAUSED,
    CONTINUE_SETUP,
    READY,
}

internal data class OnboardingEntryState(
    val languageSelected: Boolean,
    val consentAccepted: Boolean,
    val consentDeferred: Boolean,
    val moneySetupDone: Boolean,
    val permissionOnboardingDone: Boolean,
) {
    fun nextStep(): OnboardingStep {
        return when {
            !languageSelected -> OnboardingStep.LANGUAGE
            !consentAccepted -> OnboardingStep.PURPOSE_AND_CONSENT
            !permissionOnboardingDone -> OnboardingStep.PERMISSIONS
            !moneySetupDone -> OnboardingStep.MONEY_SETUP
            else -> OnboardingStep.COMPLETE
        }
    }

    fun shouldAutoOpenOnLaunch(): Boolean {
        return when (nextStep()) {
            OnboardingStep.LANGUAGE -> true
            OnboardingStep.PURPOSE_AND_CONSENT -> !consentDeferred
            OnboardingStep.MONEY_SETUP -> true
            OnboardingStep.PERMISSIONS -> true
            OnboardingStep.COMPLETE -> false
        }
    }

    fun homePrimaryActionState(): HomePrimaryActionState {
        return if (nextStep() == OnboardingStep.COMPLETE) {
            HomePrimaryActionState.START_MONITORING
        } else {
            HomePrimaryActionState.RESUME_SETUP
        }
    }

    fun homeStatusState(): HomeStatusState {
        return when {
            !languageSelected -> HomeStatusState.CHOOSE_LANGUAGE
            !consentAccepted && consentDeferred -> HomeStatusState.SETUP_PAUSED
            !consentAccepted -> HomeStatusState.REVIEW_CONSENT
            !moneySetupDone || !permissionOnboardingDone -> HomeStatusState.CONTINUE_SETUP
            else -> HomeStatusState.READY
        }
    }
}
