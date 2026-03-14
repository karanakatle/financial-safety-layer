package com.arthamantri.android

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OnboardingEntryStateTest {
    @Test
    fun `launch starts with language when language not selected`() {
        val state = OnboardingEntryState(
            languageSelected = false,
            consentAccepted = false,
            consentDeferred = false,
            moneySetupDone = false,
            permissionOnboardingDone = false,
        )

        assertEquals(OnboardingStep.LANGUAGE, state.nextStep())
        assertTrue(state.shouldAutoOpenOnLaunch())
        assertEquals(HomePrimaryActionState.RESUME_SETUP, state.homePrimaryActionState())
        assertEquals(HomeStatusState.CHOOSE_LANGUAGE, state.homeStatusState())
    }

    @Test
    fun `launch auto opens consent only when not deferred`() {
        val state = OnboardingEntryState(
            languageSelected = true,
            consentAccepted = false,
            consentDeferred = false,
            moneySetupDone = false,
            permissionOnboardingDone = false,
        )

        assertEquals(OnboardingStep.PURPOSE_AND_CONSENT, state.nextStep())
        assertTrue(state.shouldAutoOpenOnLaunch())
        assertEquals(HomeStatusState.REVIEW_CONSENT, state.homeStatusState())
    }

    @Test
    fun `deferred consent keeps resume path visible without auto opening`() {
        val state = OnboardingEntryState(
            languageSelected = true,
            consentAccepted = false,
            consentDeferred = true,
            moneySetupDone = false,
            permissionOnboardingDone = false,
        )

        assertEquals(OnboardingStep.PURPOSE_AND_CONSENT, state.nextStep())
        assertFalse(state.shouldAutoOpenOnLaunch())
        assertEquals(HomePrimaryActionState.RESUME_SETUP, state.homePrimaryActionState())
        assertEquals(HomeStatusState.SETUP_PAUSED, state.homeStatusState())
    }

    @Test
    fun `permissions come before money setup after consent`() {
        val state = OnboardingEntryState(
            languageSelected = true,
            consentAccepted = true,
            consentDeferred = false,
            moneySetupDone = false,
            permissionOnboardingDone = false,
        )

        assertEquals(OnboardingStep.PERMISSIONS, state.nextStep())
        assertTrue(state.shouldAutoOpenOnLaunch())
        assertEquals(HomePrimaryActionState.RESUME_SETUP, state.homePrimaryActionState())
        assertEquals(HomeStatusState.CONTINUE_SETUP, state.homeStatusState())
    }

    @Test
    fun `complete setup returns monitoring state`() {
        val state = OnboardingEntryState(
            languageSelected = true,
            consentAccepted = true,
            consentDeferred = false,
            moneySetupDone = true,
            permissionOnboardingDone = true,
        )

        assertEquals(OnboardingStep.COMPLETE, state.nextStep())
        assertFalse(state.shouldAutoOpenOnLaunch())
        assertEquals(HomePrimaryActionState.START_MONITORING, state.homePrimaryActionState())
        assertEquals(HomeStatusState.READY, state.homeStatusState())
    }
}
