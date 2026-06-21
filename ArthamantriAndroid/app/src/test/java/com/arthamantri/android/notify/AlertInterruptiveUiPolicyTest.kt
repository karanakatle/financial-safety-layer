package com.arthamantri.android.notify

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AlertInterruptiveUiPolicyTest {
    @Test
    fun `interruptive UI is suppressed when keyguard is locked`() {
        assertFalse(
            AlertInterruptiveUiPolicy.shouldAttempt(
                allowOverlay = true,
                keyguardLocked = true,
            ),
        )
    }

    @Test
    fun `interruptive UI is allowed only when overlays are allowed and device is unlocked`() {
        assertTrue(
            AlertInterruptiveUiPolicy.shouldAttempt(
                allowOverlay = true,
                keyguardLocked = false,
            ),
        )
        assertFalse(
            AlertInterruptiveUiPolicy.shouldAttempt(
                allowOverlay = false,
                keyguardLocked = false,
            ),
        )
    }
}
