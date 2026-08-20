package br.com.deskrudder.app

import android.content.Context
import org.json.JSONObject

/** Persistência local do endpoint UnifiedPush e do clique da notificação (#737). */
internal object UnifiedPushStore {
    private const val PREFS = "deskrudder_push"
    private const val KEY_ENDPOINT = "endpoint"
    private const val KEY_P256DH = "p256dh"
    private const val KEY_AUTH = "auth"
    private const val KEY_PENDING = "pending_open"
    const val EXTRA_PAYLOAD = "deskrudder_push_payload"

    data class Endpoint(val url: String, val p256dh: String, val auth: String)

    private fun prefs(context: Context) =
        context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun saveEndpoint(context: Context, url: String, p256dh: String, auth: String) {
        prefs(context).edit()
            .putString(KEY_ENDPOINT, url)
            .putString(KEY_P256DH, p256dh)
            .putString(KEY_AUTH, auth)
            .apply()
    }

    fun loadEndpoint(context: Context): Endpoint? {
        val p = prefs(context)
        val url = p.getString(KEY_ENDPOINT, null)?.trim().orEmpty()
        val p256dh = p.getString(KEY_P256DH, null)?.trim().orEmpty()
        val auth = p.getString(KEY_AUTH, null)?.trim().orEmpty()
        if (url.isEmpty() || p256dh.isEmpty() || auth.isEmpty()) return null
        return Endpoint(url, p256dh, auth)
    }

    fun clearEndpoint(context: Context) {
        prefs(context).edit()
            .remove(KEY_ENDPOINT)
            .remove(KEY_P256DH)
            .remove(KEY_AUTH)
            .apply()
    }

    fun savePendingOpen(context: Context, payloadJson: String) {
        prefs(context).edit().putString(KEY_PENDING, payloadJson).apply()
    }

    fun consumePendingOpen(context: Context): String? {
        val p = prefs(context)
        val raw = p.getString(KEY_PENDING, null)
        if (!raw.isNullOrBlank()) {
            p.edit().remove(KEY_PENDING).apply()
            return raw
        }
        return null
    }

    fun payloadToJson(raw: String): JSONObject {
        return try {
            JSONObject(raw)
        } catch (_: Exception) {
            JSONObject().put("titulo", "DeskRudder").put("corpo", raw.take(200))
        }
    }
}
