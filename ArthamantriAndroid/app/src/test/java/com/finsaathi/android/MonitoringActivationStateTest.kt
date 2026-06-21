package com.finsaathi.android

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MonitoringActivationStateTest {
    private fun completePermissions() = PermissionOnboardingState(
        smsGranted = true,
        usageGranted = true,
        overlayGranted = true,
        notificationsGranted = true,
    )

    @Test
    fun `onboarding blocker takes priority before permission blockers`() {
        val state = MonitoringActivationState(
            onboardingStep = OnboardingStep.MONEY_SETUP,
            permissionState = completePermissions(),
        )

        assertEquals(MonitoringStartBlocker.ONBOARDING, state.blocker())
        assertFalse(state.canStart())
    }

    @Test
    fun `permission blockers are reported in setup order`() {
        assertEquals(
            MonitoringStartBlocker.SMS,
            MonitoringActivationState(
                onboardingStep = OnboardingStep.COMPLETE,
                permissionState = PermissionOnboardingState(
                    smsGranted = false,
                    usageGranted = true,
                    overlayGranted = true,
                    notificationsGranted = true,
                ),
            ).blocker(),
        )
        assertEquals(
            MonitoringStartBlocker.USAGE,
            MonitoringActivationState(
                onboardingStep = OnboardingStep.COMPLETE,
                permissionState = PermissionOnboardingState(
                    smsGranted = true,
                    usageGranted = false,
                    overlayGranted = true,
                    notificationsGranted = true,
                ),
            ).blocker(),
        )
        assertEquals(
            MonitoringStartBlocker.NOTIFICATIONS,
            MonitoringActivationState(
                onboardingStep = OnboardingStep.COMPLETE,
                permissionState = PermissionOnboardingState(
                    smsGranted = true,
                    usageGranted = false,
                    overlayGranted = true,
                    notificationsGranted = false,
                ),
            ).blocker(),
        )
        assertEquals(
            MonitoringStartBlocker.OVERLAY,
            MonitoringActivationState(
                onboardingStep = OnboardingStep.COMPLETE,
                permissionState = PermissionOnboardingState(
                    smsGranted = true,
                    usageGranted = true,
                    overlayGranted = false,
                    notificationsGranted = true,
                ),
            ).blocker(),
        )
        assertEquals(
            MonitoringStartBlocker.NOTIFICATIONS,
            MonitoringActivationState(
                onboardingStep = OnboardingStep.COMPLETE,
                permissionState = PermissionOnboardingState(
                    smsGranted = true,
                    usageGranted = true,
                    overlayGranted = true,
                    notificationsGranted = false,
                ),
            ).blocker(),
        )
    }

    @Test
    fun `complete onboarding and permissions can start monitoring`() {
        val state = MonitoringActivationState(
            onboardingStep = OnboardingStep.COMPLETE,
            permissionState = completePermissions(),
        )

        assertEquals(MonitoringStartBlocker.NONE, state.blocker())
        assertTrue(state.canStart())
    }

    @Test
    fun `background monitoring runs only when active and all permissions remain granted`() {
        val stopped = MonitoringAccessState(
            monitoringActive = false,
            permissionState = completePermissions(),
        )
        val partial = MonitoringAccessState(
            monitoringActive = true,
            permissionState = PermissionOnboardingState(
                smsGranted = true,
                usageGranted = true,
                overlayGranted = false,
                notificationsGranted = true,
            ),
        )
        val full = MonitoringAccessState(
            monitoringActive = true,
            permissionState = completePermissions(),
        )

        assertEquals(MonitoringProtectionStatus.STOPPED, stopped.protectionStatus())
        assertFalse(stopped.canProcessBackgroundSignals())
        assertFalse(stopped.shouldStopBackgroundMonitoring())

        assertEquals(MonitoringProtectionStatus.PARTIAL, partial.protectionStatus())
        assertFalse(partial.canProcessBackgroundSignals())
        assertTrue(partial.shouldStopBackgroundMonitoring())

        assertEquals(MonitoringProtectionStatus.FULL, full.protectionStatus())
        assertTrue(full.canProcessBackgroundSignals())
        assertFalse(full.shouldStopBackgroundMonitoring())
    }
}
