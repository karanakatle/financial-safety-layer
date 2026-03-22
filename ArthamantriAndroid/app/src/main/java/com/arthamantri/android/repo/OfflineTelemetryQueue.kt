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
                request.context_event?.let { event ->
                    put("context_event", JSONObject().apply {
                        put("event_type", event.event_type)
                        put("source_app", event.source_app)
                        put("target_app", event.target_app)
                        put("correlation_id", event.correlation_id)
                        put("classification", event.classification)
                        put("setup_state", event.setup_state)
                        put("suppression_reason", event.suppression_reason)
                        put("message_family", event.message_family)
                        put("amount", event.amount)
                        put("has_otp", event.has_otp)
                        put("has_upi_handle", event.has_upi_handle)
                        put("has_upi_deeplink", event.has_upi_deeplink)
                        put("has_url", event.has_url)
                        put("metadata", JSONObject(event.metadata))
                    })
                }
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
                                context_event = payload.optJSONObject("context_event")?.let { event ->
                                    com.arthamantri.android.model.PilotContextEvent(
                                        event_type = event.optString("event_type"),
                                        source_app = event.optString("source_app").takeIf { it.isNotBlank() },
                                        target_app = event.optString("target_app").takeIf { it.isNotBlank() },
                                        correlation_id = event.optString("correlation_id").takeIf { it.isNotBlank() },
                                        classification = event.optString("classification").takeIf { it.isNotBlank() },
                                        setup_state = event.optString("setup_state").takeIf { it.isNotBlank() },
                                        suppression_reason = event.optString("suppression_reason").takeIf { it.isNotBlank() },
                                        message_family = event.optString("message_family").takeIf { it.isNotBlank() },
                                        amount = if (event.has("amount")) event.optDouble("amount") else null,
                                        has_otp = event.opt("has_otp").takeIf { it != null } as? Boolean,
                                        has_upi_handle = event.opt("has_upi_handle").takeIf { it != null } as? Boolean,
                                        has_upi_deeplink = event.opt("has_upi_deeplink").takeIf { it != null } as? Boolean,
                                        has_url = event.opt("has_url").takeIf { it != null } as? Boolean,
                                        metadata = buildMap {
                                            val metadata = event.optJSONObject("metadata")
                                            if (metadata != null) {
                                                val keys = metadata.keys()
                                                while (keys.hasNext()) {
                                                    val key = keys.next()
                                                    put(key, metadata.optString(key))
                                                }
                                            }
                                        },
                                    )
                                },
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
