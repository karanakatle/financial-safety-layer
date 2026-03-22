package com.arthamantri.android.core

import android.content.Context
import android.util.Log
import com.arthamantri.android.BuildConfig
import com.arthamantri.android.repo.LiteracyRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

object DebugObservability {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    fun enabled(): Boolean = BuildConfig.DEBUG

    suspend fun trace(
        context: Context,
        tag: String,
        event: String,
        fields: Map<String, String?> = emptyMap(),
    ) {
        if (!enabled()) {
            return
        }
        val message = buildString {
            append("debug_trace:")
            append(event)
            fields
                .filterValues { !it.isNullOrBlank() }
                .toSortedMap()
                .forEach { (key, value) ->
                    append(" ")
                    append(key)
                    append("=")
                    append(value)
                }
        }
        Log.d(tag, message)
        LiteracyRepository.submitAppLog(
            context = context,
            level = AppConstants.Domain.PILOT_LOG_LEVEL_INFO,
            message = message,
            language = LiteracyRepository.language(context),
            participantId = LiteracyRepository.participantId(context),
        )
    }

    fun traceAsync(
        context: Context,
        tag: String,
        event: String,
        fields: Map<String, String?> = emptyMap(),
    ) {
        if (!enabled()) {
            return
        }
        scope.launch {
            trace(
                context = context,
                tag = tag,
                event = event,
                fields = fields,
            )
        }
    }
}
