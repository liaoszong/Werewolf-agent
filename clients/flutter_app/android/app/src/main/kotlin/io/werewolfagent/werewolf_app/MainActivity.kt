package io.werewolfagent.werewolf_app

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.FileProvider
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.security.MessageDigest

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "werewolf_app/apk_installer",
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "getUpdateCacheDirectory" -> {
                    result.success(File(cacheDir, "werewolf_updates").absolutePath)
                }
                "inspectApkArchive" -> handleInspectApkArchive(call, result)
                "installApk" -> handleInstallApk(call, result)
                else -> result.notImplemented()
            }
        }
    }

    private fun handleInspectApkArchive(call: MethodCall, result: MethodChannel.Result) {
        val path = call.argument<String>("path")
        if (path.isNullOrBlank()) {
            result.error("APK_PATH_MISSING", "APK path is required.", null)
            return
        }

        val apkFile = File(path)
        if (!apkFile.exists()) {
            result.error("APK_FILE_NOT_FOUND", "APK file does not exist.", null)
            return
        }

        try {
            val archiveInfo = packageManager.getPackageArchiveInfo(
                apkFile.absolutePath,
                packageInfoSignatureFlags(),
            )
            if (archiveInfo == null) {
                result.error("APK_ARCHIVE_INVALID", "Unable to read APK archive.", null)
                return
            }
            val archiveSignatures = archiveInfo.signaturesCompat()
            val firstSignature = archiveSignatures.firstOrNull()
            if (firstSignature == null) {
                result.error("APK_ARCHIVE_UNSIGNED", "APK archive has no signing certificate.", null)
                return
            }

            result.success(
                mapOf(
                    "packageName" to archiveInfo.packageName,
                    "versionCode" to archiveInfo.versionCodeCompat(),
                    "signingCertificateSha256" to sha256Hex(firstSignature.toByteArray()),
                    "isSignatureCompatible" to isSignatureCompatible(archiveInfo),
                ),
            )
        } catch (error: Exception) {
            result.error("APK_ARCHIVE_INSPECTION_FAILED", error.message, null)
        }
    }

    private fun handleInstallApk(call: MethodCall, result: MethodChannel.Result) {
        val path = call.argument<String>("path")
        if (path.isNullOrBlank()) {
            result.error("APK_PATH_MISSING", "APK path is required.", null)
            return
        }

        val apkFile = File(path)
        if (!apkFile.exists()) {
            result.error("APK_FILE_NOT_FOUND", "APK file does not exist.", null)
            return
        }

        try {
            val uri = FileProvider.getUriForFile(
                this,
                "$packageName.apk_provider",
                apkFile,
            )
            val intent = Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, "application/vnd.android.package-archive")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            startActivity(intent)
            result.success(null)
        } catch (error: Exception) {
            result.error("APK_INSTALL_FAILED", error.message, null)
        }
    }

    private fun isSignatureCompatible(archiveInfo: android.content.pm.PackageInfo): Boolean {
        val installedInfo = packageManager.getPackageInfo(packageName, packageInfoSignatureFlags())
        val archiveHashes = archiveInfo.signaturesCompat()
            .map { sha256Hex(it.toByteArray()) }
            .toSet()
        val installedHashes = installedInfo.signaturesCompat()
            .map { sha256Hex(it.toByteArray()) }
            .toSet()
        return archiveHashes.isNotEmpty() && installedHashes.isNotEmpty() &&
            archiveHashes.intersect(installedHashes).isNotEmpty()
    }

    private fun packageInfoSignatureFlags(): Int {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            PackageManager.GET_SIGNING_CERTIFICATES
        } else {
            @Suppress("DEPRECATION")
            PackageManager.GET_SIGNATURES
        }
    }
}

private fun android.content.pm.PackageInfo.versionCodeCompat(): Long {
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
        longVersionCode
    } else {
        @Suppress("DEPRECATION")
        versionCode.toLong()
    }
}

private fun android.content.pm.PackageInfo.signaturesCompat(): Array<android.content.pm.Signature> {
    return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
        val info = signingInfo ?: return emptyArray()
        if (info.hasMultipleSigners()) {
            info.apkContentsSigners ?: emptyArray()
        } else {
            info.signingCertificateHistory ?: emptyArray()
        }
    } else {
        @Suppress("DEPRECATION")
        signatures ?: emptyArray()
    }
}

private fun sha256Hex(bytes: ByteArray): String {
    val digest = MessageDigest.getInstance("SHA-256").digest(bytes)
    return digest.joinToString("") { "%02x".format(it.toInt() and 0xff) }
}
