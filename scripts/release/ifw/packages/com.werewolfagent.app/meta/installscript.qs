function Component() {}

Component.prototype.createOperations = function() {
    component.createOperations();

    // Create desktop shortcut
    component.addOperation("CreateShortcut",
        "@TargetDir@/Werewolf-agent.exe",
        "@DesktopDir@/Werewolf-agent.lnk",
        "workingDirectory=@TargetDir@");

    // Create Start Menu shortcut
    component.addOperation("CreateShortcut",
        "@TargetDir@/Werewolf-agent.exe",
        "@StartMenuDir@/Werewolf-agent.lnk",
        "workingDirectory=@TargetDir@");
};

Component.prototype.createOperationsForUninstall = function() {
    component.createOperationsForUninstall();
    // Note: default uninstall does NOT remove %LOCALAPPDATA%\Werewolf-agent\
    // That is only done if the user checks "delete local data" via the installer
    // uninstaller GUI (handled by IFW built-in data directory removal option)
};

Component.prototype.performUninstallation = function() {
    var dataRoot = installer.environmentVariable("LOCALAPPDATA") + "/Werewolf-agent";
    var result = QMessageBox.question(
        "Werewolf-agent",
        "是否删除本地对局、配置、日志与运行时数据？\n\n"
        + "此操作不会删除 API 凭证与偏好设置。\n\n"
        + "Delete local matches, configs, logs, and runtime data?\n\n"
        + "API credentials and preferences will not be removed.",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    );
    if (result === QMessageBox.Yes) {
        component.addOperation("Rmdir", dataRoot);
    }
    component.performUninstallation();
};
