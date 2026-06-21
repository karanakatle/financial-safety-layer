package com.finsaathi.android

import com.finsaathi.android.core.AppConstants
import org.junit.Assert.assertEquals
import org.junit.Test

class ReleaseIdentifierMigrationTest {
    @Test
    fun `debug build uses FinSaathi application id with dev suffix`() {
        assertEquals("com.finsaathi.android.dev", BuildConfig.APPLICATION_ID)
    }

    @Test
    fun `persistent identifiers use FinSaathi names before public release`() {
        assertEquals("finsaathi_prefs", AppConstants.Prefs.PILOT_PREFS)
        assertEquals("finsaathi_android_prefs", AppConstants.Prefs.APP_CONFIG_PREFS)
        assertEquals("finsaathi_safety_alerts", AppConstants.Notifications.SAFETY_CHANNEL_ID)
        assertEquals("finsaathi_savings_nudges", AppConstants.Notifications.SAVINGS_CHANNEL_ID)
        assertEquals(
            "com.finsaathi.android.action.RUN_SAVINGS_NUDGE",
            AppConstants.BroadcastActions.RUN_SAVINGS_NUDGE,
        )
    }
}
