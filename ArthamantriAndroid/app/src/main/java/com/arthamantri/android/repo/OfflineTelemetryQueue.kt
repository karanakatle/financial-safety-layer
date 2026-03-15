package com.arthamantri.android.repo

import android.content.Context
import android.util.Log
import com.arthamantri.android.api.ApiClient
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.model.LiteracyAlertFeedbackRequest
import com.arthamantri.android.model.PilotAppLogRequest
import org.json.JSONArray
import org.json.JSONObject

object OfflineTelemetryQueue {
    private const val FIELD_KIND = "kind"
    private const val FIELD_PAYLOAD = "payload"

    suspend fun enqueueAlertFeedback(
        context: Context,
        request: LiteracyAlertFeedbackRequest,
    ) {
        enqueue(
            context = context,
            kind = AppConstants.Domain.OFFLINE_QUEUE_KIND_ALERT_FEEDBACK,
            payload = JSONObject().apply {
                put("event_id", request.event_id)
                put("alert_id", request.alert_id)
                put("participant_id", request.participant_id)
                put("action", request.action)
                put("channel", request.channel)
                put("title", request.title)
                put("message", request.message)
                put("timestamp", request.timestamp)
            },
        )
    }

    suspend fun enqueueAppLog(
        context: Context,
        request: PilotAppLogRequest,
    ) {
        enqueue(
            context = context,
            kind = AppConstants.Domain.OFFLINE_QUEUE_KIND_APP_LOG,
            payload = JSONObject().apply {
                put("event_id", request.event_id)
                put("participant_id", request.participant_id)
                put("level", request.level)
                put("message", request.message)
                put("language", request.language)
                put("timestamp", request.timestamp)
            },
        )
    }

    suspend fun flush(context: Context): Int {
        val queue = readQueue(context).toMutableList()
        if (queue.isEmpty()) {
            return 0
        }
        val api = ApiClient.literacyApi(context)
        var flushedCount = 0
        val remaining = mutableListOf<JSONObject>()
        for ((index, item) in queue.withIndex()) {
            val kind = item.optString(FIELD_KIND)
            val payload = item.optJSONObject(FIELD_PAYLOAD) ?: continue
            val delivered = runCatching {
                when (kind) {
                    AppConstants.Domain.OFFLINE_QUEUE_KIND_ALERT_FEEDBACK -> {
                        api.alertFeedback(
                            LiteracyAlertFeedbackRequest(
                                event_id = payload.optString("event_id").takeIf { it.isNotBlank() },
                                alert_id = payload.optString("alert_id"),
                                participant_id = payload.optString("participant_id"),
                                action = payload.optString("action"),
                                channel = payload.optString("channel"),
                                title = payload.optString("title"),
                                message = payload.optString("message"),
                                timestamp = payload.optString("timestamp").takeIf { it.isNotBlank() },
                            )
                        ).ok
                    }

                    AppConstants.Domain.OFFLINE_QUEUE_KIND_APP_LOG -> {
                        api.pilotAppLog(
                            PilotAppLogRequest(
                                event_id = payload.optString("event_id").takeIf { it.isNotBlank() },
                                participant_id = payload.optString("participant_id"),
                                level = payload.optString("level"),
                                message = payload.optString("message"),
                                language = payload.optString("language"),
                                timestamp = payload.optString("timestamp").takeIf { it.isNotBlank() },
                            )
                        ).ok
                    }

                    else -> true
                }
            }.getOrElse {
                Log.w(
                    AppConstants.LogTags.MAIN_ACTIVITY,
                    "Offline queue flush stopped on $kind",
                    it,
                )
                remaining.add(item)
                remaining.addAll(queue.drop(index + 1))
                writeQueue(context, remaining)
                return flushedCount
            }

            if (delivered) {
                flushedCount += 1
            } else {
                remaining.add(item)
                remaining.addAll(queue.drop(index + 1))
                writeQueue(context, remaining)
                return flushedCount
            }
        }
        writeQueue(context, emptyList())
        return flushedCount
    }

    private fun enqueue(
        context: Context,
        kind: String,
        payload: JSONObject,
    ) {
        val queue = readQueue(context).toMutableList()
        queue.add(
            JSONObject().apply {
                put(FIELD_KIND, kind)
                put(FIELD_PAYLOAD, payload)
            }
        )
        val bounded = if (queue.size > AppConstants.Timing.OFFLINE_QUEUE_MAX_ITEMS) {
            queue.takeLast(AppConstants.Timing.OFFLINE_QUEUE_MAX_ITEMS)
        } else {
            queue
        }
        writeQueue(context, bounded)
    }

    private fun readQueue(context: Context): List<JSONObject> {
        val prefs = context.getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        val raw = prefs.getString(AppConstants.Prefs.KEY_OFFLINE_TELEMETRY_QUEUE, null).orEmpty()
        if (raw.isBlank()) {
            return emptyList()
        }
        return runCatching {
            val array = JSONArray(raw)
            buildList {
                for (index in 0 until array.length()) {
                    val item = array.optJSONObject(index) ?: continue
                    add(item)
                }
            }
        }.getOrElse {
            emptyList()
        }
    }

    private fun writeQueue(context: Context, items: List<JSONObject>) {
        val array = JSONArray()
        items.forEach { array.put(it) }
        context.getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(AppConstants.Prefs.KEY_OFFLINE_TELEMETRY_QUEUE, array.toString())
            .apply()
    }
}
