import java.io.File
import java.util.Properties
import org.gradle.api.GradleException

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

data class ChannelSigning(
    val channel: String,
    val propertiesFileName: String,
    val requirePropertyName: String,
    val configName: String,
)

data class LoadedSigning(
    val channel: String,
    val configName: String,
    val keyAlias: String?,
    val keyPassword: String?,
    val storePassword: String?,
    val storeFile: File?,
    val enabled: Boolean,
)

fun Properties.readNonBlank(name: String): String? =
    getProperty(name)?.trim()?.takeIf { it.isNotEmpty() }

fun resolveSigningStoreFile(pathValue: String?): File? {
    val normalized = pathValue?.trim()?.takeIf { it.isNotEmpty() } ?: return null
    val directFile = File(normalized)
    if (directFile.isAbsolute) {
        return directFile
    }

    val candidates = linkedSetOf(
        rootProject.file(normalized),
        file(normalized),
    )
    return candidates.firstOrNull { it.exists() } ?: candidates.firstOrNull()
}

fun isRequired(name: String): Boolean =
    project.findProperty(name)
        ?.toString()
        ?.trim()
        ?.equals("true", ignoreCase = true) == true

val channelSignings = listOf(
    ChannelSigning(
        channel = "internal",
        propertiesFileName = "internal-key.properties",
        requirePropertyName = "requireInternalSigning",
        configName = "internalRelease",
    ),
    ChannelSigning(
        channel = "production",
        propertiesFileName = "production-key.properties",
        requirePropertyName = "requireProductionSigning",
        configName = "productionRelease",
    ),
)

fun loadSigning(channelSigning: ChannelSigning): LoadedSigning {
    val propertiesFile = rootProject.file(channelSigning.propertiesFileName)
    val required = isRequired(channelSigning.requirePropertyName)
    if (required && !propertiesFile.exists()) {
        throw GradleException(
            "Android ${channelSigning.channel} signing is required, but ${propertiesFile.path} does not exist.",
        )
    }

    val properties = Properties().apply {
        if (propertiesFile.exists()) {
            propertiesFile.inputStream().use { load(it) }
        }
    }
    if (!propertiesFile.exists()) {
        return LoadedSigning(
            channel = channelSigning.channel,
            configName = channelSigning.configName,
            keyAlias = null,
            keyPassword = null,
            storePassword = null,
            storeFile = null,
            enabled = false,
        )
    }

    val missingSigningFields = listOf(
        "storeFile",
        "storePassword",
        "keyAlias",
        "keyPassword",
    ).filter { properties.readNonBlank(it) == null }

    if (missingSigningFields.isNotEmpty()) {
        throw GradleException(
            "Android ${channelSigning.channel} signing config is incomplete in ${propertiesFile.path}: " +
                "missing or blank ${missingSigningFields.joinToString(", ")}.",
        )
    }

    val storeFile = resolveSigningStoreFile(properties.readNonBlank("storeFile"))
        ?: throw GradleException(
            "Android ${channelSigning.channel} signing storeFile cannot be resolved from ${propertiesFile.path}.",
        )

    if (!storeFile.exists()) {
        throw GradleException(
            "Android ${channelSigning.channel} signing storeFile does not exist: ${storeFile.path}.",
        )
    }

    return LoadedSigning(
        channel = channelSigning.channel,
        configName = channelSigning.configName,
        keyAlias = properties.readNonBlank("keyAlias"),
        keyPassword = properties.readNonBlank("keyPassword"),
        storePassword = properties.readNonBlank("storePassword"),
        storeFile = storeFile,
        enabled = true,
    )
}

val loadedSignings = channelSignings.associate { it.channel to loadSigning(it) }

android {
    namespace = "io.werewolfagent.werewolf_app"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        loadedSignings.values
            .filter { it.enabled }
            .forEach { loaded ->
                create(loaded.configName) {
                    storeFile = loaded.storeFile!!
                    storePassword = loaded.storePassword!!
                    keyAlias = loaded.keyAlias!!
                    keyPassword = loaded.keyPassword!!
                }
            }
    }

    flavorDimensions += "channel"
    productFlavors {
        create("internal") {
            dimension = "channel"
            applicationId = "io.werewolfagent.werewolf_app.internal"
            resValue("string", "app_name", "Werewolf Agent Internal")
            signingConfig = signingConfigs.getByName(
                if (loadedSignings.getValue("internal").enabled) "internalRelease" else "debug",
            )
        }
        create("production") {
            dimension = "channel"
            applicationId = "io.werewolfagent.werewolf_app"
            resValue("string", "app_name", "Werewolf Agent")
            signingConfig = signingConfigs.getByName(
                if (loadedSignings.getValue("production").enabled) "productionRelease" else "debug",
            )
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            isShrinkResources = false
        }
    }
}

flutter {
    source = "../.."
}

dependencies {
    implementation("androidx.core:core:1.13.1")
}
