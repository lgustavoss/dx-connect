package br.com.deskrudder.app

import android.Manifest
import android.content.Intent
import android.os.Build
import com.getcapacitor.JSObject
import com.getcapacitor.PermissionState
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.getcapacitor.annotation.Permission
import com.getcapacitor.annotation.PermissionCallback
import org.json.JSONObject
import org.unifiedpush.android.connector.UnifiedPush
import java.lang.ref.WeakReference

@CapacitorPlugin(
    name = "DeskRudderUnifiedPush",
    permissions = [
        Permission(
            alias = "notifications",
            strings = [Manifest.permission.POST_NOTIFICATIONS],
        ),
    ],
)
class UnifiedPushPlugin : Plugin() {
    @PluginMethod
    fun registerPush(call: PluginCall) {
        val vapid = call.getString("vapidPublicKey")?.trim().orEmpty()
        if (vapid.isEmpty()) {
            call.reject("sem_vapid")
            return
        }
        if (needsNotificationPermission() && getPermissionState("notifications") != PermissionState.GRANTED) {
            requestPermissionForAlias("notifications", call, "onNotificationsPermission")
            return
        }
        startRegistration(call, vapid)
    }

    @PermissionCallback
    fun onNotificationsPermission(call: PluginCall) {
        if (getPermissionState("notifications") != PermissionState.GRANTED) {
            call.reject("negado")
            return
        }
        val vapid = call.getString("vapidPublicKey")?.trim().orEmpty()
        if (vapid.isEmpty()) {
            call.reject("sem_vapid")
            return
        }
        startRegistration(call, vapid)
    }

    @PluginMethod
    fun unregisterPush(call: PluginCall) {
        try {
            UnifiedPush.unregister(context)
        } catch (_: Exception) {
            /* logout continua */
        }
        UnifiedPushStore.clearEndpoint(context)
        call.resolve()
    }

    @PluginMethod
    fun consumePendingOpen(call: PluginCall) {
        val fromIntent = activity?.intent?.getStringExtra(UnifiedPushStore.EXTRA_PAYLOAD)
        if (!fromIntent.isNullOrBlank()) {
            activity?.intent?.removeExtra(UnifiedPushStore.EXTRA_PAYLOAD)
            call.resolve(jsonToJs(UnifiedPushStore.payloadToJson(fromIntent)))
            return
        }
        val pending = UnifiedPushStore.consumePendingOpen(context)
        if (pending.isNullOrBlank()) {
            call.resolve(JSObject())
            return
        }
        call.resolve(jsonToJs(UnifiedPushStore.payloadToJson(pending)))
    }

    override fun load() {
        instance = WeakReference(this)
    }

    override fun handleOnNewIntent(intent: Intent?) {
        super.handleOnNewIntent(intent)
        val raw = intent?.getStringExtra(UnifiedPushStore.EXTRA_PAYLOAD) ?: return
        // Limpar EXTRA para o consumePendingOpen no JS não reabrir o mesmo deep link.
        intent.removeExtra(UnifiedPushStore.EXTRA_PAYLOAD)
        activity?.intent?.removeExtra(UnifiedPushStore.EXTRA_PAYLOAD)
        emitOpen(raw)
    }

    private fun startRegistration(call: PluginCall, vapid: String) {
        val act = activity
        if (act == null) {
            call.reject("indisponivel")
            return
        }
        pendingRegister = call
        try {
            UnifiedPush.tryUseCurrentOrDefaultDistributor(act) { success ->
                if (!success) {
                    completeRegisterError("indisponivel")
                    return@tryUseCurrentOrDefaultDistributor
                }
                try {
                    UnifiedPush.register(
                        context,
                        "default",
                        "DeskRudder",
                        vapid,
                    )
                } catch (_: UnifiedPush.VapidNotValidException) {
                    completeRegisterError("sem_vapid")
                } catch (_: Exception) {
                    completeRegisterError("indisponivel")
                }
            }
        } catch (_: Exception) {
            completeRegisterError("indisponivel")
        }
    }

    private fun completeRegisterError(code: String) {
        val call = pendingRegister ?: return
        pendingRegister = null
        call.reject(code)
    }

    private fun deliverEndpoint(url: String, p256dh: String, auth: String) {
        val data = JSObject()
            .put("endpoint", url)
            .put("p256dh", p256dh)
            .put("auth", auth)
        notifyListeners("endpoint", data, true)
        val call = pendingRegister
        if (call != null) {
            pendingRegister = null
            call.resolve(data)
        }
    }

    private fun deliverOpen(raw: String) {
        notifyListeners("open", jsonToJs(UnifiedPushStore.payloadToJson(raw)), true)
    }

    private fun deliverRegistrationError(reason: String) {
        val data = JSObject().put("reason", reason)
        notifyListeners("registrationError", data, true)
        completeRegisterError(if (reason.contains("NETWORK", ignoreCase = true)) "indisponivel" else "indisponivel")
    }

    private fun needsNotificationPermission(): Boolean = Build.VERSION.SDK_INT >= 33

    companion object {
        private var instance: WeakReference<UnifiedPushPlugin>? = null
        @Volatile
        private var pendingRegister: PluginCall? = null

        fun emitEndpoint(url: String, p256dh: String, auth: String) {
            instance?.get()?.deliverEndpoint(url, p256dh, auth)
        }

        fun emitOpen(raw: String) {
            instance?.get()?.deliverOpen(raw)
        }

        fun emitRegistrationError(reason: String) {
            instance?.get()?.deliverRegistrationError(reason)
        }

        fun emitUnregistered() {
            instance?.get()?.notifyListeners("unregistered", JSObject(), false)
        }

        private fun jsonToJs(obj: JSONObject): JSObject {
            val out = JSObject()
            val tipo = obj.optString("tipo")
            if (tipo.isNotBlank()) out.put("tipo", tipo)
            if (obj.has("id") && !obj.isNull("id")) out.put("id", obj.optLong("id"))
            val urlPath = obj.optString("url_path")
            if (urlPath.isNotBlank()) out.put("url_path", urlPath)
            val titulo = obj.optString("titulo")
            if (titulo.isNotBlank()) out.put("titulo", titulo)
            val corpo = obj.optString("corpo")
            if (corpo.isNotBlank()) out.put("corpo", corpo)
            return out
        }
    }
}
