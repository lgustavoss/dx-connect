package br.com.deskrudder.app

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import org.unifiedpush.android.connector.FailedReason
import org.unifiedpush.android.connector.PushService
import org.unifiedpush.android.connector.data.PushEndpoint
import org.unifiedpush.android.connector.data.PushMessage

/**
 * Recebe eventos UnifiedPush com a app em segundo plano ou fechada (#737).
 * O payload é o JSON Web Push já usado pela PWA (`tipo`, `id`, `titulo`, `url_path`, `corpo`).
 */
class DeskRudderPushService : PushService() {
    override fun onNewEndpoint(endpoint: PushEndpoint, instance: String) {
        val keys = endpoint.pubKeySet ?: return
        UnifiedPushStore.saveEndpoint(this, endpoint.url, keys.pubKey, keys.auth)
        UnifiedPushPlugin.emitEndpoint(endpoint.url, keys.pubKey, keys.auth)
    }

    override fun onMessage(message: PushMessage, instance: String) {
        val raw = try {
            String(message.content, Charsets.UTF_8)
        } catch (_: Exception) {
            "{}"
        }
        // Só mostra o alerta. A mesa só abre no toque (PendingIntent → handleOnNewIntent),
        // como a PWA (notificationclick). Não gravar pending nem emitir "open" aqui:
        // senão a app em primeiro plano saltava sozinha, e o próximo arranque
        // reabria o último push mesmo sem clique.
        showNotification(raw)
    }

    override fun onRegistrationFailed(reason: FailedReason, instance: String) {
        UnifiedPushPlugin.emitRegistrationError(reason.name)
    }

    override fun onUnregistered(instance: String) {
        UnifiedPushStore.clearEndpoint(this)
        UnifiedPushPlugin.emitUnregistered()
    }

    private fun showNotification(raw: String) {
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }
        ensureChannel()
        val data = UnifiedPushStore.payloadToJson(raw)
        val titulo = data.optString("titulo").ifBlank { "DeskRudder" }
        val corpo = data.optString("corpo").ifBlank { "Nova actividade no atendimento" }
        val tipo = data.optString("tipo")
        val id = data.optLong("id", 0L)
        val tag = "${tipo.ifBlank { "push" }}:$id"

        val tap = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                Intent.FLAG_ACTIVITY_CLEAR_TOP or
                Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra(UnifiedPushStore.EXTRA_PAYLOAD, raw)
        }
        val pending = PendingIntent.getActivity(
            this,
            tag.hashCode(),
            tap,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_notify)
            .setContentTitle(titulo)
            .setContentText(corpo)
            .setAutoCancel(true)
            .setContentIntent(pending)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setDefaults(NotificationCompat.DEFAULT_ALL)
            .build()
        NotificationManagerCompat.from(this).notify(tag.hashCode(), notification)
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NotificationManager::class.java) ?: return
        if (manager.getNotificationChannel(CHANNEL_ID) != null) return
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ID,
                "Alertas de atendimento",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = "Fila e mensagens nos teus chats e tickets"
            },
        )
    }

    companion object {
        private const val CHANNEL_ID = "deskrudder_push"
    }
}
