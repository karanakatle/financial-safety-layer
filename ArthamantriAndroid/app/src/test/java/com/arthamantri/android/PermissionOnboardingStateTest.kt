package com.arthamantri.android

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PermissionOnboardingStateTest {
    @Test
    fun `permission ordering stays sms notifications usage overlay`() {
        assertEquals(
            PermissionStep.SMS,
            PermissionOnboardingState(false, false, false, false).nextStep(),
        )
        assertEquals(
            PermissionStep.NOTIFICATIONS,
            PermissionOnboardingState(true, false, false, false).nextStep(),
        )
        assertEquals(
            PermissionStep.USAGE,
            PermissionOnboardingState(true, false, false, true).nextStep(),
        )
        assertEquals(
            PermissionStep.OVERLAY,
            PermissionOnboardingState(true, true, false, true).nextStep(),
        )
    }

    @Test
    fun `remaining steps stay visible until all permissions are granted`() {
        val state = PermissionOnboardingState(
            smsGranted = true,
            usageGranted = false,
            overlayGranted = true,
            notificationsGranted = false,
        )

        assertFalse(state.isComplete())
        assertEquals(2, state.completedCount())
        assertEquals(listOf(PermissionStep.NOTIFICATIONS, PermissionStep.USAGE), state.remainingSteps())
    }

    @Test
    fun `all granted marks permission onboarding complete`() {
        val state = PermissionOnboardingState(
            smsGranted = true,
            usageGranted = true,
            overlayGranted = true,
            notificationsGranted = true,
        )

        assertTrue(state.isComplete())
        assertEquals(PermissionStep.COMPLETE, state.nextStep())
        assertEquals(4, state.completedCount())
        assertTrue(state.remainingSteps().isEmpty())
    }

    @Test
    fun `guided flow resumes only while permissions remain`() {
        val incomplete = PermissionOnboardingState(
            smsGranted = true,
            usageGranted = false,
            overlayGranted = false,
            notificationsGranted = false,
        )
        val complete = PermissionOnboardingState(
            smsGranted = true,
            usageGranted = true,
            overlayGranted = true,
            notificationsGranted = true,
        )

        assertTrue(incomplete.shouldAutoResume(guidedFlowActive = true))
        assertFalse(incomplete.shouldStopGuidedFlow(guidedFlowActive = true))
        assertFalse(complete.shouldAutoResume(guidedFlowActive = true))
        assertTrue(complete.shouldStopGuidedFlow(guidedFlowActive = true))
    }
}
