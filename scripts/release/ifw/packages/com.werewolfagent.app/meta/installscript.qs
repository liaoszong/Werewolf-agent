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

// Custom page for data cleanup option
Component.prototype.setDefaultPageVisible = function(pageId, visible) {
    if (pageId === QInstaller.PerformUninstallation) {
        // Show custom checkbox for data cleanup
        installer.setValue("DeleteUserData", "false");
    }
};
