package br.com.deskrudder.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat

/**
 * Notificação persistente de plantão enquanto há chats na fila.
 * Mantém o processo mais vivo com a tela bloqueada (lock/unlock).
 */
class FilaAlertForegroundService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                stopSelf()
                return START_NOT_STICKY
            }
            else -> {
                val count = intent?.getIntExtra(EXTRA_COUNT, 0) ?: 0
                if (count <= 0) {
                    stopSelf()
                    return START_NOT_STICKY
                }
                ensureChannel()
                val notification = buildNotification(count)
                if (Build.VERSION.SDK_INT >= 34) {
                    ServiceCompat.startForeground(
                        this,
                        NOTIFY_ID,
                        notification,
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE,
                    )
                } else {
                    startForeground(NOTIFY_ID, notification)
                }
                return START_STICKY
            }
        }
    }

    override fun onDestroy() {
        stopForeground(STOP_FOREGROUND_REMOVE)
        super.onDestroy()
    }

    private fun buildNotification(count: Int): Notification {
        val body =
            if (count == 1) "Há 1 chat aguardando atendimento"
            else "Há $count chats aguardando atendimento"
        val tap = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                Intent.FLAG_ACTIVITY_CLEAR_TOP or
                Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra(
                UnifiedPushStore.EXTRA_PAYLOAD,
                """{"tipo":"chat.fila","url_path":"/chat/espera"}""",
            )
        }
        val pending = PendingIntent.getActivity(
            this,
            NOTIFY_ID,
            tap,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_notify)
            .setContentTitle("DeskRudder — plantão")
            .setContentText(body)
            .setOngoing(true)
            .setOnlyAlertOnce(false)
            .setContentIntent(pending)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setDefaults(NotificationCompat.DEFAULT_ALL)
            .build()
    }

    private fun ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = getSystemService(NotificationManager::class.java) ?: return
        if (manager.getNotificationChannel(CHANNEL_ID) != null) return
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ID,
                "Fila de espera",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = "Plantão: clientes aguardando atendimento no chat"
                enableVibration(true)
                setSound(
                    android.media.RingtoneManager.getDefaultUri(
                        android.media.RingtoneManager.TYPE_NOTIFICATION,
                    ),
                    null,
                )
                setShowBadge(true)
            },
        )
    }

    companion object {
        const val CHANNEL_ID = "deskrudder_fila"
        const val NOTIFY_ID = 82302
        const val EXTRA_COUNT = "count"
        const val ACTION_STOP = "br.com.deskrudder.app.STOP_FILA_ALERT"
        const val ACTION_UPDATE = "br.com.deskrudder.app.UPDATE_FILA_ALERT"

        fun start(context: Context, count: Int) {
            val intent = Intent(context, FilaAlertForegroundService::class.java).apply {
                action = ACTION_UPDATE
                putExtra(EXTRA_COUNT, count)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            val intent = Intent(context, FilaAlertForegroundService::class.java).apply {
                action = ACTION_STOP
            }
            context.startService(intent)
        }
    }
}
