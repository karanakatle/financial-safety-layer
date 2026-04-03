package com.arthamantri.android.savings

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Calendar

class SavingsNudgeSchedulerTest {
    @Test
    fun nextTrigger_rolls_to_same_day_when_before_8pm() {
        val now = Calendar.getInstance().apply {
            set(2026, Calendar.APRIL, 4, 18, 30, 0)
            set(Calendar.MILLISECOND, 0)
        }

        val trigger = SavingsNudgeScheduler.nextTriggerAtMillis(now)
        val resolved = Calendar.getInstance().apply { timeInMillis = trigger }

        assertEquals(2026, resolved.get(Calendar.YEAR))
        assertEquals(Calendar.APRIL, resolved.get(Calendar.MONTH))
        assertEquals(4, resolved.get(Calendar.DAY_OF_MONTH))
        assertEquals(20, resolved.get(Calendar.HOUR_OF_DAY))
        assertEquals(0, resolved.get(Calendar.MINUTE))
    }

    @Test
    fun nextTrigger_rolls_to_next_day_when_after_8pm() {
        val now = Calendar.getInstance().apply {
            set(2026, Calendar.APRIL, 4, 21, 5, 0)
            set(Calendar.MILLISECOND, 0)
        }

        val trigger = SavingsNudgeScheduler.nextTriggerAtMillis(now)
        val resolved = Calendar.getInstance().apply { timeInMillis = trigger }

        assertEquals(5, resolved.get(Calendar.DAY_OF_MONTH))
        assertEquals(20, resolved.get(Calendar.HOUR_OF_DAY))
        assertTrue(trigger > now.timeInMillis)
    }
}
